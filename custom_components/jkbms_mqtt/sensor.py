"""sensor platform: static catalog rows plus dynamic per-cell entities."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory

from .const import CELL_SENSOR_CATALOG, DOMAIN, MAX_CELLS, SENSOR_CATALOG
from .payloads import to_float, unique_id_for

# diagnostics kept as raw strings, never coerced to float
_RAW_TOPICS = frozenset({"error_bitmask", "alarms"})

# cosmetic display precision per catalog topic
_SUGGESTED_PRECISION = {
    "voltage": 3,
    "current": 3,
    "power": 1,
    "soc": 0,
    "soh": 0,
    "capacity_remaining": 2,
    "capacity_nominal": 2,
    "cycles": 0,
    "runtime_s": 0,
    "temperature/mos": 1,
    "temperature/1": 1,
    "temperature/2": 1,
    "balancing_current": 3,
    "heating_current": 3,
}
_CELL_PRECISION = {"voltage": 3, "resistance": 3}

# every dynamic cell field the bridge may publish
_CELL_FIELDS = tuple(
    ("cell", str(index), kind)
    for index in range(1, MAX_CELLS + 1)
    for kind in CELL_SENSOR_CATALOG
)


def _sensor_device_class(name):
    return None if name is None else SensorDeviceClass(name)


def _state_class(name):
    return None if name is None else SensorStateClass(name)


def _entity_category(name):
    return None if name is None else EntityCategory(name)


class DeviceAvailabilityMixin:
    """every entity of a device inherits its availability flag."""

    @property
    def available(self):
        return self.jkbms_device.online


class JkbmsEntity(DeviceAvailabilityMixin):
    """shared registration and availability plumbing for both platforms."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator, device):
        self.coordinator = coordinator
        self.jkbms_device = device
        self._field = ()

    @property
    def device_info(self):
        return self.jkbms_device.device_info()

    async def async_added_to_hass(self):
        self.coordinator.register_device_listener(
            self.jkbms_device.name, self._value_changed
        )
        self.coordinator.register(
            self.jkbms_device.name, self._field, self._value_changed
        )

    async def async_will_remove_from_hass(self):
        self.coordinator.unregister(
            self.jkbms_device.name, self._field, self._value_changed
        )
        self.coordinator.unregister_device_listener(
            self.jkbms_device.name, self._value_changed
        )

    @callback
    def _value_changed(self):
        self.async_write_ha_state()


class JkbmsSensor(JkbmsEntity, SensorEntity):
    """one static sensor catalog row."""

    def __init__(self, coordinator, device, catalog_row):
        super().__init__(coordinator, device)
        self._catalog_row = catalog_row
        self._field = tuple(catalog_row["topic"].split("/"))
        self._attr_name = catalog_row["name"]
        self._attr_unique_id = unique_id_for(device.name, self._field)
        self._attr_device_class = _sensor_device_class(catalog_row["device_class"])
        self._attr_native_unit_of_measurement = catalog_row["unit"]
        self._attr_state_class = _state_class(catalog_row["state_class"])
        self._attr_entity_category = _entity_category(catalog_row["entity_category"])
        self._attr_suggested_display_precision = _SUGGESTED_PRECISION.get(
            catalog_row["topic"]
        )

    @property
    def native_value(self):
        raw = self.jkbms_device.values.get(self._field)
        if raw is None:
            return None
        topic = self._catalog_row["topic"]
        if topic == "online":
            # already a datetime, converted by the coordinator
            return raw
        if topic in _RAW_TOPICS:
            return raw
        return to_float(raw)


class JkbmsCellSensor(JkbmsSensor):
    """dynamic per-cell entity created when its topic first arrives."""

    def __init__(self, coordinator, device, kind, index):
        template = CELL_SENSOR_CATALOG[kind]
        row = {
            "topic": f"cell/{index}/{kind}",
            "name": template["name"].format(index=index),
            "device_class": template["device_class"],
            "unit": template["unit"],
            "state_class": template["state_class"],
            "entity_category": template["entity_category"],
        }
        super().__init__(coordinator, device, row)
        self._attr_suggested_display_precision = _CELL_PRECISION.get(kind)


def _entities_for_device(coordinator, device):
    entities = [JkbmsSensor(coordinator, device, row) for row in SENSOR_CATALOG]
    entities.extend(
        JkbmsCellSensor(coordinator, device, field[2], int(field[1]))
        for field in _CELL_FIELDS
        if field in device.values
    )
    return entities


def _watch_dynamic_fields(coordinator, device, async_add_entities):
    # one-shot factories append the dynamic entity on its first payload
    for field in _CELL_FIELDS:
        if field in device.values:
            continue

        def _factory(payload, device=device, field=field):
            async_add_entities(
                [JkbmsCellSensor(coordinator, device, field[2], int(field[1]))]
            )

        coordinator.register_first_value(device.name, field, _factory)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    for device in list(coordinator.devices.values()):
        async_add_entities(_entities_for_device(coordinator, device))
        _watch_dynamic_fields(coordinator, device, async_add_entities)

    @callback
    def _on_new_device(name):
        device = coordinator.devices.get(name)
        if device is None:
            return
        async_add_entities(_entities_for_device(coordinator, device))
        _watch_dynamic_fields(coordinator, device, async_add_entities)

    coordinator.new_device_callbacks.append(_on_new_device)
