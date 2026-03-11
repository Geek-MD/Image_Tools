"""Image processing utilities for the Image Tools integration."""
from __future__ import annotations

import logging
import os
from typing import Any

from PIL import Image, ImageOps
from PIL.Image import Resampling

from .const import ASPECT_MODE_CROP, ASPECT_MODE_LETTERBOX, SUPPORTED_FORMATS

_LOGGER = logging.getLogger(__name__)


class ImageProcessor:
    """Handles image processing operations using Pillow."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resize_image(
        self,
        input_path: str,
        output_path: str,
        width: int | None = None,
        height: int | None = None,
        keep_aspect_ratio: bool = True,
        target_aspect_ratio: float | None = None,
        aspect_mode: str = ASPECT_MODE_CROP,
    ) -> dict[str, Any]:
        """Resize an image to given dimensions, optionally adjusting aspect ratio.

        Args:
            input_path: Full path to the source image.
            output_path: Full path for the output image.
            width: Target width in pixels (optional).
            height: Target height in pixels (optional).
            keep_aspect_ratio: Preserve the original aspect ratio when resizing.
            target_aspect_ratio: Desired aspect ratio (width / height). When set
                the image will be cropped or letterboxed before resizing.
            aspect_mode: How to apply ``target_aspect_ratio`` — ``crop``,
                ``letterbox``, or ``stretch``.

        Returns:
            dict with ``success`` bool and operation details.
        """
        if width is None and height is None and target_aspect_ratio is None:
            return {
                "success": False,
                "error": "At least one of width, height or target_aspect_ratio must be specified",
            }

        try:
            with Image.open(input_path) as img:
                orig_width, orig_height = img.size

                # --- 1. Aspect ratio adjustment ---
                if target_aspect_ratio is not None:
                    img = self._apply_aspect_ratio(img, target_aspect_ratio, aspect_mode)

                # --- 2. Resize ---
                if width is not None or height is not None:
                    img = self._resize(img, width, height, keep_aspect_ratio)

                new_width, new_height = img.size

                # --- 3. Save ---
                img = self._prepare_for_save(img, output_path)
                self._ensure_output_dir(output_path)
                fmt = self._format_for_path(output_path)
                _save_kwargs: dict[str, Any] = {}
                if fmt == "JPEG":
                    _save_kwargs["quality"] = 95
                    _save_kwargs["optimize"] = True
                img.save(output_path, fmt, **_save_kwargs)

            _LOGGER.info(
                "Resized image %s → %s (%dx%d → %dx%d)",
                input_path,
                output_path,
                orig_width,
                orig_height,
                new_width,
                new_height,
            )
            return {
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "original_size": [orig_width, orig_height],
                "new_size": [new_width, new_height],
            }
        except FileNotFoundError:
            _LOGGER.error("Image file not found: %s", input_path)
            return {"success": False, "error": f"Image file not found: {input_path}"}
        except OSError as err:
            _LOGGER.error("I/O error resizing image %s: %s", input_path, err)
            return {"success": False, "error": str(err)}
        except Exception as err:  # noqa: BLE001 — final safety net for unexpected Pillow errors
            _LOGGER.exception("Unexpected error resizing image %s", input_path)
            return {"success": False, "error": str(err)}

    def convert_image(
        self,
        input_path: str,
        output_path: str,
        output_format: str,
    ) -> dict[str, Any]:
        """Convert an image to a different format.

        Args:
            input_path: Full path to the source image.
            output_path: Full path for the output image.
            output_format: Target format key (e.g. ``"jpg"``, ``"png"``).

        Returns:
            dict with ``success`` bool and operation details.
        """
        fmt_key = output_format.lower()
        pillow_fmt = SUPPORTED_FORMATS.get(fmt_key)
        if pillow_fmt is None:
            return {
                "success": False,
                "error": f"Unsupported output format: {output_format}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}",
            }

        try:
            with Image.open(input_path) as img:
                orig_format = img.format or "unknown"
                img = self._prepare_for_save(img, output_path, pillow_fmt)
                self._ensure_output_dir(output_path)
                _save_kwargs: dict[str, Any] = {}
                if pillow_fmt == "JPEG":
                    _save_kwargs["quality"] = 95
                    _save_kwargs["optimize"] = True
                img.save(output_path, pillow_fmt, **_save_kwargs)

            _LOGGER.info(
                "Converted image %s (%s) → %s (%s)",
                input_path,
                orig_format,
                output_path,
                pillow_fmt,
            )
            return {
                "success": True,
                "input_path": input_path,
                "output_path": output_path,
                "original_format": orig_format.lower(),
                "output_format": fmt_key,
            }
        except FileNotFoundError:
            _LOGGER.error("Image file not found: %s", input_path)
            return {"success": False, "error": f"Image file not found: {input_path}"}
        except OSError as err:
            _LOGGER.error("I/O error converting image %s: %s", input_path, err)
            return {"success": False, "error": str(err)}
        except Exception as err:  # noqa: BLE001 — final safety net for unexpected Pillow errors
            _LOGGER.exception("Unexpected error converting image %s", input_path)
            return {"success": False, "error": str(err)}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resize(
        img: Image.Image,
        width: int | None,
        height: int | None,
        keep_aspect_ratio: bool,
    ) -> Image.Image:
        """Return a resized copy of *img*."""
        orig_w, orig_h = img.size

        if keep_aspect_ratio:
            if width and height:
                # Scale to fit inside the box (thumbnail behaviour)
                img.thumbnail((width, height), Resampling.LANCZOS)
                return img
            if width:
                ratio = width / orig_w
                new_h = max(1, round(orig_h * ratio))
                return img.resize((width, new_h), Resampling.LANCZOS)
            # height only
            ratio = (height or orig_h) / orig_h
            new_w = max(1, round(orig_w * ratio))
            return img.resize((new_w, height or orig_h), Resampling.LANCZOS)

        # Stretch / ignore aspect ratio
        new_w = width or orig_w
        new_h = height or orig_h
        return img.resize((new_w, new_h), Resampling.LANCZOS)

    @staticmethod
    def _apply_aspect_ratio(
        img: Image.Image,
        target: float,
        mode: str,
    ) -> Image.Image:
        """Adjust *img* to *target* aspect ratio using the given *mode*."""
        orig_w, orig_h = img.size
        current = orig_w / orig_h

        if abs(current - target) < 0.001:
            return img

        if mode == ASPECT_MODE_CROP:
            # Crop to target aspect ratio (centre crop)
            if current > target:
                # Image is wider than target → crop width
                new_w = round(orig_h * target)
                left = (orig_w - new_w) // 2
                return img.crop((left, 0, left + new_w, orig_h))
            # Image is taller than target → crop height
            new_h = round(orig_w / target)
            top = (orig_h - new_h) // 2
            return img.crop((0, top, orig_w, top + new_h))

        if mode == ASPECT_MODE_LETTERBOX:
            # Add black bars to reach target aspect ratio
            if current > target:
                # Image is wider → add top/bottom bars
                new_h = round(orig_w / target)
                return ImageOps.pad(img, (orig_w, new_h), color=(0, 0, 0))
            # Image is taller → add left/right bars
            new_w = round(orig_h * target)
            return ImageOps.pad(img, (new_w, orig_h), color=(0, 0, 0))

        # ASPECT_MODE_STRETCH — caller resizes freely, nothing to do here
        return img

    @staticmethod
    def _prepare_for_save(
        img: Image.Image,
        output_path: str,
        pillow_fmt: str | None = None,
    ) -> Image.Image:
        """Convert colour mode if required for the target format."""
        if pillow_fmt is None:
            pillow_fmt = ImageProcessor._format_for_path(output_path)
        if pillow_fmt == "JPEG" and img.mode not in ("RGB", "L"):
            return img.convert("RGB")
        if pillow_fmt == "BMP" and img.mode == "RGBA":
            return img.convert("RGB")
        return img

    @staticmethod
    def _format_for_path(output_path: str) -> str:
        """Derive the Pillow format string from *output_path* extension."""
        ext = os.path.splitext(output_path)[1].lower().lstrip(".")
        return SUPPORTED_FORMATS.get(ext, "PNG")

    @staticmethod
    def _ensure_output_dir(output_path: str) -> None:
        """Create parent directory of *output_path* if it does not exist."""
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
