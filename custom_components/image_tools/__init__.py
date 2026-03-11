"""The Image Tools integration."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import SupportsResponse

from .const import (
    ASPECT_MODE_CROP,
    DOMAIN,
    VALID_ASPECT_MODES,
    VALID_OUTPUT_FORMATS,
)
from .image_processor import ImageProcessor

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Service names
SERVICE_RESIZE_IMAGE = "resize_image"
SERVICE_CONVERT_IMAGE = "convert_image"

# Service schemas
SERVICE_RESIZE_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("input_path"): cv.string,
        vol.Optional("output_path"): cv.string,
        vol.Optional("overwrite", default=False): cv.boolean,
        vol.Optional("width"): cv.positive_int,
        vol.Optional("height"): cv.positive_int,
        vol.Optional("keep_aspect_ratio", default=True): cv.boolean,
        vol.Optional("target_aspect_ratio"): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=10.0)
        ),
        vol.Optional("aspect_mode", default=ASPECT_MODE_CROP): vol.In(
            VALID_ASPECT_MODES
        ),
    }
)

SERVICE_CONVERT_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required("input_path"): cv.string,
        vol.Optional("output_path"): cv.string,
        vol.Optional("overwrite", default=False): cv.boolean,
        vol.Required("output_format"): vol.In(VALID_OUTPUT_FORMATS),
    }
)


async def _ensure_event_processed() -> None:
    """Yield to event loop so that fired events are dispatched immediately.

    Calling this right after ``hass.bus.async_fire()`` prevents race conditions
    where the service completes before automations can react to the event.
    """
    await asyncio.sleep(0)


def _resolve_output_path(
    input_path: str,
    output_path: str | None,
    overwrite: bool,
    suffix: str = "_processed",
    new_ext: str | None = None,
) -> str:
    """Return the effective output path for a service call.

    Args:
        input_path: Source file path.
        output_path: Explicit output path supplied by the caller (may be None).
        overwrite: When True the original file will be overwritten.
        suffix: Appended before the extension when auto-generating the name.
        new_ext: Replace extension when auto-generating (without leading dot).

    Returns:
        Resolved output file path.
    """
    if overwrite:
        return input_path
    if output_path:
        return output_path
    # Auto-generate: same directory, new name
    base, ext = os.path.splitext(input_path)
    if new_ext:
        ext = f".{new_ext}"
    return f"{base}{suffix}{ext}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Image Tools from a config entry."""
    _LOGGER.info("Setting up Image Tools integration")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "work_dir": entry.data.get("work_dir", ""),
    }

    processor = ImageProcessor()
    hass.data[DOMAIN]["processor"] = processor

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # ------------------------------------------------------------------
    # Service: resize_image
    # ------------------------------------------------------------------
    async def handle_resize_image(call: ServiceCall) -> dict[str, Any] | None:
        """Handle the resize_image service call."""
        input_path: str = call.data["input_path"]
        output_path_raw: str | None = call.data.get("output_path")
        overwrite: bool = call.data.get("overwrite", False)
        width: int | None = call.data.get("width")
        height: int | None = call.data.get("height")
        keep_aspect_ratio: bool = call.data.get("keep_aspect_ratio", True)
        target_aspect_ratio: float | None = call.data.get("target_aspect_ratio")
        aspect_mode: str = call.data.get("aspect_mode", ASPECT_MODE_CROP)

        output_path = _resolve_output_path(
            input_path, output_path_raw, overwrite, suffix="_resized"
        )

        _LOGGER.info("Resizing image: %s → %s", input_path, output_path)
        start_time = time.time()

        sensor = hass.data[DOMAIN].get("sensor")
        if sensor:
            sensor.set_working("resize")

        processes_performed: list[str] = []

        try:
            result: dict[str, Any] = await hass.async_add_executor_job(
                lambda: processor.resize_image(
                    input_path=input_path,
                    output_path=output_path,
                    width=width,
                    height=height,
                    keep_aspect_ratio=keep_aspect_ratio,
                    target_aspect_ratio=target_aspect_ratio,
                    aspect_mode=aspect_mode,
                )
            )
        except OSError as err:
            result = {"success": False, "error": str(err)}
        except Exception as err:  # noqa: BLE001 — safety net for unexpected executor errors
            _LOGGER.exception("Unexpected error in resize_image executor job")
            result = {"success": False, "error": str(err)}

        elapsed = time.time() - start_time

        if result["success"]:
            processes_performed.append("resize")
            _LOGGER.info(
                "Image resized successfully in %.2fs: %s", elapsed, output_path
            )
            job_result = "success"
        else:
            _LOGGER.error(
                "Image resize failed in %.2fs: %s — %s",
                elapsed,
                input_path,
                result.get("error"),
            )
            job_result = "failed"

        hass.bus.async_fire(
            f"{DOMAIN}_image_processing_finished",
            {
                "operation": "resize",
                "input_path": input_path,
                "output_path": output_path if result["success"] else None,
                "result": job_result,
                "error": result.get("error"),
            },
        )
        await _ensure_event_processed()

        if sensor:
            sensor.set_idle(job_result, processes_performed)

        if call.return_response:
            return {
                "success": result["success"],
                "output_path": result.get("output_path"),
                "original_size": result.get("original_size"),
                "new_size": result.get("new_size"),
                "error": result.get("error"),
            }
        return None

    # ------------------------------------------------------------------
    # Service: convert_image
    # ------------------------------------------------------------------
    async def handle_convert_image(call: ServiceCall) -> dict[str, Any] | None:
        """Handle the convert_image service call."""
        input_path: str = call.data["input_path"]
        output_path_raw: str | None = call.data.get("output_path")
        overwrite: bool = call.data.get("overwrite", False)
        output_format: str = call.data["output_format"]

        # Normalise the extension alias (jpeg → jpg)
        ext_map = {"jpeg": "jpg", "tif": "tiff"}
        output_ext = ext_map.get(output_format.lower(), output_format.lower())

        output_path = _resolve_output_path(
            input_path,
            output_path_raw,
            overwrite,
            suffix="_converted",
            new_ext=output_ext,
        )

        _LOGGER.info(
            "Converting image: %s → %s (%s)", input_path, output_path, output_format
        )
        start_time = time.time()

        sensor = hass.data[DOMAIN].get("sensor")
        if sensor:
            sensor.set_working("convert")

        processes_performed: list[str] = []

        try:
            result: dict[str, Any] = await hass.async_add_executor_job(
                lambda: processor.convert_image(
                    input_path=input_path,
                    output_path=output_path,
                    output_format=output_format,
                )
            )
        except OSError as err:
            result = {"success": False, "error": str(err)}
        except Exception as err:  # noqa: BLE001 — safety net for unexpected executor errors
            _LOGGER.exception("Unexpected error in convert_image executor job")
            result = {"success": False, "error": str(err)}

        elapsed = time.time() - start_time

        if result["success"]:
            processes_performed.append("convert")
            _LOGGER.info(
                "Image converted successfully in %.2fs: %s", elapsed, output_path
            )
            job_result = "success"
        else:
            _LOGGER.error(
                "Image conversion failed in %.2fs: %s — %s",
                elapsed,
                input_path,
                result.get("error"),
            )
            job_result = "failed"

        hass.bus.async_fire(
            f"{DOMAIN}_image_processing_finished",
            {
                "operation": "convert",
                "input_path": input_path,
                "output_path": output_path if result["success"] else None,
                "output_format": output_format,
                "result": job_result,
                "error": result.get("error"),
            },
        )
        await _ensure_event_processed()

        if sensor:
            sensor.set_idle(job_result, processes_performed)

        if call.return_response:
            return {
                "success": result["success"],
                "output_path": result.get("output_path"),
                "original_format": result.get("original_format"),
                "output_format": output_format,
                "error": result.get("error"),
            }
        return None

    # ------------------------------------------------------------------
    # Register services
    # ------------------------------------------------------------------
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESIZE_IMAGE,
        handle_resize_image,
        schema=SERVICE_RESIZE_IMAGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONVERT_IMAGE,
        handle_convert_image,
        schema=SERVICE_CONVERT_IMAGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    _LOGGER.info("Image Tools services registered successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Image Tools integration")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    hass.services.async_remove(DOMAIN, SERVICE_RESIZE_IMAGE)
    hass.services.async_remove(DOMAIN, SERVICE_CONVERT_IMAGE)

    if DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not any(
            k
            for k in hass.data[DOMAIN]
            if k not in ("processor", "sensor")
        ):
            hass.data[DOMAIN].pop("processor", None)
            hass.data[DOMAIN].pop("sensor", None)

    return True
