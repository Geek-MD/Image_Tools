"""Config flow for the Image Tools integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_WORK_DIR, DEFAULT_WORK_DIR, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ImageToolsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for Image Tools."""

    VERSION = 1

    # Only one instance of this integration is needed
    SINGLE_CONFIG_ENTRY = True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial configuration step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            work_dir = user_input.get(CONF_WORK_DIR, DEFAULT_WORK_DIR).strip()
            return self.async_create_entry(
                title="Image Tools",
                data={CONF_WORK_DIR: work_dir},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_WORK_DIR, default=DEFAULT_WORK_DIR): str,
                }
            ),
            errors=errors,
        )
