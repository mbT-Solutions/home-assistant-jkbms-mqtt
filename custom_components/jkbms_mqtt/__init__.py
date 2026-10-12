"""config entry setup: coordinator lifecycle and platform forwarding."""

from .const import DOMAIN
from .coordinator import JkbmsMqttCoordinator

PLATFORMS = ("sensor", "binary_sensor")


async def async_setup_entry(hass, entry):
    coordinator = JkbmsMqttCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.listen()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass, entry):
    # options flow wrote a new prefix into entry data; reload resubscribes
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        coordinator.stop()
    return unload_ok
