"""config and options flow: a single configurable topic prefix field."""

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_PREFIX, DEFAULT_PREFIX, DOMAIN
from .topology import sanitize_prefix


def _schema(default):
    return vol.Schema({vol.Required(CONF_PREFIX, default=default): str})


class JkbmsMqttConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """one entry per sanitized prefix; multiple entries are allowed."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            prefix = sanitize_prefix(user_input.get(CONF_PREFIX))
            await self.async_set_unique_id(prefix)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"JK BMS ({prefix})", data={CONF_PREFIX: prefix}
            )
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(DEFAULT_PREFIX),
            description_placeholders={"default_prefix": DEFAULT_PREFIX},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return JkbmsMqttOptionsFlowHandler()


class JkbmsMqttOptionsFlowHandler(config_entries.OptionsFlow):
    """change the prefix live; the entry reloads via its update listener."""

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            prefix = sanitize_prefix(user_input.get(CONF_PREFIX))
            # canonical prefix lives in entry data, options stay empty
            self.hass.config_entries.async_update_entry(
                self.config_entry, data={CONF_PREFIX: prefix}
            )
            return self.async_create_entry(title="", data={})
        current = self.config_entry.options.get(
            CONF_PREFIX, self.config_entry.data.get(CONF_PREFIX, DEFAULT_PREFIX)
        )
        return self.async_show_form(
            step_id="init",
            data_schema=_schema(current),
            description_placeholders={"default_prefix": DEFAULT_PREFIX},
        )
