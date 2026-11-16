from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST

from . import DOMAIN, ERRORS, DucoApi


class DucoConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                board = await DucoApi(self.hass, user_input[CONF_HOST]).get("board_info")
            except ERRORS:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(board["mac"])
                self._abort_if_unique_id_configured(updates=user_input)
                return self.async_create_entry(title="Duco", data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )
