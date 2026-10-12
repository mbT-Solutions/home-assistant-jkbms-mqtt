"""coordinator: subscribes <prefix>/#, maintains devices, fans out updates.

pure routing logic lives at module level so tests can import it without
homeassistant; the mqtt import is deferred into listen().
"""

from dataclasses import dataclass

from .const import AVAILABILITY_TOPIC, CONF_PREFIX, DEVICE_INFO_TOPICS
from .device import JkbmsDevice, changed_info_fields
from .payloads import epoch_to_datetime
from .topology import sanitize_prefix, split_topic

try:
    # marks _route to always run on the event loop; tests import without ha
    from homeassistant.core import callback as _ha_callback
except ImportError:  # pragma: no cover - exercised only outside home assistant
    def _ha_callback(func):
        return func

KIND_VALUE = "value"
KIND_AVAILABILITY = "availability"
KIND_INFO = "info"
KIND_UNKNOWN = "unknown"

_KINDS = frozenset({KIND_VALUE, KIND_AVAILABILITY, KIND_INFO, KIND_UNKNOWN})

# kinds that signal a device-wide change to device listeners
_SIGNAL_KINDS = frozenset({KIND_AVAILABILITY, KIND_INFO})


@dataclass(frozen=True)
class RoutingDecision:
    """how a received message must be applied; kind in the KIND_* constants."""

    device: str
    field: tuple
    kind: str


def parse_message(topic, payload, prefix):
    """pure routing decision for one message; none when the topic is not ours.

    unknown subtopics stay kind "value" for forward compatibility; a message
    without a concrete device/field is kind "unknown" and never applied.
    """
    split = split_topic(topic, prefix)
    if split is None:
        return None
    device, field = split
    if not device or not field or any(not segment for segment in field):
        return RoutingDecision(device, field, KIND_UNKNOWN)
    if field == (AVAILABILITY_TOPIC,):
        return RoutingDecision(device, field, KIND_AVAILABILITY)
    if len(field) == 1 and field[0] in DEVICE_INFO_TOPICS:
        return RoutingDecision(device, field, KIND_INFO)
    return RoutingDecision(device, field, KIND_VALUE)


class JkbmsMqttCoordinator:
    """one config entry: route messages under the prefix to devices/entities."""

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.prefix = sanitize_prefix(entry.data[CONF_PREFIX])
        self.devices = {}
        # (device name, field tuple) -> set of entity callbacks
        self._listeners = {}
        # device name -> callbacks for availability/device-info changes
        self._device_listeners = {}
        # (device name, field tuple) -> one-shot first-value factories
        self._first_value = {}
        # platform callbacks appended on platform setup
        self.new_device_callbacks = []
        self._remove_sub = None

    async def listen(self):
        # deferred so importing this module never requires homeassistant
        from homeassistant.components import mqtt

        self._remove_sub = await mqtt.async_subscribe(
            self.hass, f"{self.prefix}/#", self._route
        )

    def stop(self):
        if self._remove_sub is not None:
            self._remove_sub()
            self._remove_sub = None
        self.devices.clear()
        self._listeners.clear()
        self._device_listeners.clear()
        self._first_value.clear()
        self.new_device_callbacks.clear()

    @_ha_callback
    def _route(self, msg):
        payload = msg.payload
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError:
                return
        decision = parse_message(msg.topic, payload, self.prefix)
        if decision is None or decision.kind == KIND_UNKNOWN:
            return
        name = decision.device
        field = decision.field
        device = self.devices.get(name)
        is_new = device is None
        if is_new:
            device = self._new_device(name)
        value = payload
        if field == ("online",):
            # timestamp sensor state; conversion kept in one place
            converted = epoch_to_datetime(payload)
            if converted is not None:
                value = converted
        # latest payloads per device; plain attribute, device.py stays pure
        device.values[field] = value
        if decision.kind == KIND_AVAILABILITY:
            device.online = payload == "online"
        elif decision.kind == KIND_INFO:
            device.set_string(field[0], payload)
            self._sync_device_registry(device)
        if is_new:
            for callback in tuple(self.new_device_callbacks):
                callback(name)
        factories = self._first_value.pop((name, field), None)
        if factories is not None:
            for factory in factories:
                factory(payload)
        for callback in tuple(self._listeners.get((name, field), ())):
            callback()
        if decision.kind in _SIGNAL_KINDS:
            for callback in tuple(self._device_listeners.get(name, ())):
                callback()

    def _sync_device_registry(self, device):
        """push device-info topics into the ha device registry.

        entity_platform reads device_info only once at entity add, and the
        bridge publishes info topics after the value topics that create the
        entities; without this the registry keeps the fallbacks forever.
        """
        from homeassistant.helpers import device_registry as dr  # noqa: e402

        registry = dr.async_get(self.hass)
        entry = registry.async_get_device(
            identifiers={(self.entry.domain, device.name)}
        )
        if entry is None:
            return
        current = {
            "name": entry.name,
            "manufacturer": entry.manufacturer,
            "model": entry.model,
            "sw_version": entry.sw_version,
            "hw_version": entry.hw_version,
            "serial_number": entry.serial_number,
        }
        changes = changed_info_fields(device, current)
        if changes:
            registry.async_update_device(entry.id, **changes)

    def _new_device(self, name):
        device = JkbmsDevice(name)
        device.values = {}
        self.devices[name] = device
        return device

    def register(self, device, field, callback):
        """entity pattern: call in added_to_hass, unregister in will_remove."""
        self._listeners.setdefault((device, tuple(field)), set()).add(callback)

    def unregister(self, device, field, callback):
        key = (device, tuple(field))
        callbacks = self._listeners.get(key)
        if callbacks is None:
            return
        callbacks.discard(callback)
        if not callbacks:
            del self._listeners[key]

    def register_device_listener(self, name, callback):
        """availability/device-info changes affecting all entities of a device."""
        self._device_listeners.setdefault(name, set()).add(callback)

    def unregister_device_listener(self, name, callback):
        callbacks = self._device_listeners.get(name)
        if callbacks is None:
            return
        callbacks.discard(callback)
        if not callbacks:
            del self._device_listeners[name]

    def register_first_value(self, device, field, factory):
        """one-shot callback when the first payload for a key arrives."""
        self._first_value.setdefault((device, tuple(field)), []).append(factory)
