"""Sensor platform for the Image Tools integration."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_IDLE, STATE_WORKING

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Image Tools sensor."""
    _LOGGER.info("Setting up Image Tools sensor")

    sensor = ImageToolsSensor(entry)
    async_add_entities([sensor], True)

    # Store sensor reference so service handlers can update it
    hass.data[DOMAIN]["sensor"] = sensor


class ImageToolsSensor(SensorEntity):
    """Sensor to track Image Tools service status."""

    _attr_has_entity_name = True
    _attr_name = "Status"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{DOMAIN}_status"
        self._attr_native_value = STATE_IDLE
        self._attr_extra_state_attributes: dict[str, str | list[str] | None] = {
            "last_job": None,
            "last_operation": None,
            "timestamp": None,
            "processes": [],
        }

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Image Tools",
            manufacturer="Geek-MD",
            model="Image Processor",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def icon(self) -> str:
        """Return the icon based on current state."""
        if self._attr_native_value == STATE_WORKING:
            return "mdi:image-edit"
        return "mdi:image-check-outline"

    @callback
    def set_working(self, operation: str) -> None:
        """Set sensor to working state.

        Args:
            operation: Name of the operation starting (e.g. ``resize``, ``convert``).
        """
        self._attr_native_value = STATE_WORKING
        self._attr_extra_state_attributes["last_operation"] = operation
        self._attr_extra_state_attributes["timestamp"] = datetime.now().isoformat()
        self._attr_extra_state_attributes["processes"] = []
        self.async_write_ha_state()
        _LOGGER.info("Image Tools sensor state: working (%s)", operation)

    @callback
    def set_idle(
        self,
        job_result: str,
        processes: list[str] | None = None,
    ) -> None:
        """Set sensor to idle state with job result.

        Args:
            job_result: Result of the last job (``success`` or ``failed``).
            processes: Operations performed in the last job.
        """
        self._attr_native_value = STATE_IDLE
        self._attr_extra_state_attributes["last_job"] = job_result
        self._attr_extra_state_attributes["timestamp"] = datetime.now().isoformat()
        self._attr_extra_state_attributes["processes"] = processes or []
        self.async_write_ha_state()
        _LOGGER.info(
            "Image Tools sensor state: idle (result: %s, processes: %s)",
            job_result,
            processes,
        )
