"""binary sensor platform: flags, aggregate alarms and per-alarm entities."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory

from .const import (
    ALARM_BINARY_CATALOG,
    ALARM_SLUGS,
    BINARY_SENSOR_CATALOG,
    DOMAIN,
)
from .payloads import alarm_payload, alarms_csv_active, to_flag, unique_id_for
from .sensor import JkbmsEntity, _entity_category

_ALARM_FIELDS = tuple(("alarm", slug) for slug in ALARM_SLUGS)


def _binary_device_class(name):
    return None if name is None else BinarySensorDeviceClass(name)


class JkbmsBinarySensor(JkbmsEntity, BinarySensorEntity):
    """flag rows: on when payload is '1'."""

    def __init__(self, coordinator, device, catalog_row):
        super().__init__(coordinator, device)
        self._catalog_row = catalog_row
        self._field = tuple(catalog_row["topic"].split("/"))
        self._attr_name = catalog_row["name"]
        self._attr_unique_id = unique_id_for(device.name, self._field)
        self._attr_device_class = _binary_device_class(catalog_row["device_class"])
        self._attr_entity_category = _entity_category(catalog_row["entity_category"])

    @property
    def is_on(self):
        raw = self.jkbms_device.values.get(self._field)
        if raw is None:
            return None
        return to_flag(raw)


class JkbmsAlarmsBinarySensor(JkbmsBinarySensor):
    """aggregate alarm sensor: on while the csv holds at least one slug."""

    @property
    def is_on(self):
        raw = self.jkbms_device.values.get(self._field)
        if raw is None:
            return None
        return alarms_csv_active(raw)

    @property
    def extra_state_attributes(self):
        raw = self.jkbms_device.values.get(self._field)
        if raw is None:
            return None
        return {
            "active_alarms": [part.strip() for part in raw.split(",") if part.strip()]
        }


class JkbmsAlarmBinarySensor(JkbmsEntity, BinarySensorEntity):
    """dynamic per-alarm entity created when its alarm topic first arrives."""

    def __init__(self, coordinator, device, slug):
        super().__init__(coordinator, device)
        self._field = ("alarm", slug)
        self._attr_name = ALARM_BINARY_CATALOG["name"].format(slug=slug)
        self._attr_unique_id = unique_id_for(device.name, self._field)
        self._attr_device_class = _binary_device_class(
            ALARM_BINARY_CATALOG["device_class"]
        )
        self._attr_entity_category = _entity_category(
            ALARM_BINARY_CATALOG["entity_category"]
        )

    @property
    def is_on(self):
        raw = self.jkbms_device.values.get(self._field)
        if raw is None:
            return None
        return alarm_payload(raw)


def _entities_for_device(coordinator, device):
    entities = []
    for row in BINARY_SENSOR_CATALOG:
        if row["topic"] == "alarms":
            entities.append(JkbmsAlarmsBinarySensor(coordinator, device, row))
        else:
            entities.append(JkbmsBinarySensor(coordinator, device, row))
    entities.extend(
        JkbmsAlarmBinarySensor(coordinator, device, field[1])
        for field in _ALARM_FIELDS
        if field in device.values
    )
    return entities


def _watch_dynamic_fields(coordinator, device, async_add_entities):
    for field in _ALARM_FIELDS:
        if field in device.values:
            continue

        def _factory(payload, device=device, field=field):
            async_add_entities(
                [JkbmsAlarmBinarySensor(coordinator, device, field[1])]
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
