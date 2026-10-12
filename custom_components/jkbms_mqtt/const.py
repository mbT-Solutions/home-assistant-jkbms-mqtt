"""static constants and entity catalog tables; import-clean (no homeassistant imports)."""

DOMAIN = "jkbms_mqtt"
DEFAULT_PREFIX = "jkbms"
CONF_PREFIX = "prefix"

MAX_CELLS = 24

AVAILABILITY_TOPIC = "availability"

# 13 known bridge alarm slugs in spec order
ALARM_SLUGS = (
    "cell_undervoltage",
    "cell_overvoltage",
    "pack_undervoltage",
    "pack_overvoltage",
    "charging_overtemperature",
    "charging_undertemperature",
    "discharging_overtemperature",
    "discharging_undertemperature",
    "charging_overcurrent",
    "discharging_overcurrent",
    "short_circuit",
    "ic_error",
    "locked_mos",
)

# static sensor catalog; "topic" is the suffix below <prefix>/<name>/
SENSOR_CATALOG = (
    {
        "topic": "voltage",
        "name": "Voltage",
        "device_class": "voltage",
        "unit": "V",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "current",
        "name": "Current",
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "power",
        "name": "Power",
        "device_class": "power",
        "unit": "W",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "soc",
        "name": "State of charge",
        "device_class": "battery",
        "unit": "%",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "soh",
        "name": "State of health",
        "device_class": "battery",
        "unit": "%",
        "state_class": "measurement",
        "entity_category": None,
    },
    # ampere-hours have no standard ha device class
    {
        "topic": "capacity_remaining",
        "name": "Capacity remaining",
        "device_class": None,
        "unit": "Ah",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "capacity_nominal",
        "name": "Capacity nominal",
        "device_class": None,
        "unit": "Ah",
        "state_class": "total",
        "entity_category": None,
    },
    {
        "topic": "cycles",
        "name": "Cycles",
        "device_class": None,
        "unit": "cycles",
        "state_class": "total_increasing",
        "entity_category": None,
    },
    {
        "topic": "runtime_s",
        "name": "Total runtime",
        "device_class": "duration",
        "unit": "s",
        "state_class": "total_increasing",
        "entity_category": None,
    },
    {
        "topic": "temperature/mos",
        "name": "Temperature MOS",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "temperature/1",
        "name": "Temperature 1",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "temperature/2",
        "name": "Temperature 2",
        "device_class": "temperature",
        "unit": "°C",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "balancing_current",
        "name": "Balancing current",
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "heating_current",
        "name": "Heating current",
        "device_class": "current",
        "unit": "A",
        "state_class": "measurement",
        "entity_category": None,
    },
    {
        "topic": "online",
        "name": "Last connect",
        "device_class": "timestamp",
        "unit": None,
        "state_class": None,
        "entity_category": "diagnostic",
    },
    {
        "topic": "error_bitmask",
        "name": "Error bitmask",
        "device_class": None,
        "unit": None,
        "state_class": None,
        "entity_category": "diagnostic",
    },
    # csv payload doubles as attribute source for the aggregate alarm sensor
    {
        "topic": "alarms",
        "name": "Alarms CSV",
        "device_class": None,
        "unit": None,
        "state_class": None,
        "entity_category": "diagnostic",
    },
)

# static binary sensor catalog; mos states are plain (no problem class)
BINARY_SENSOR_CATALOG = (
    {
        "topic": "balancing",
        "name": "Balancing",
        "device_class": "battery_charging",
        "entity_category": None,
    },
    {
        "topic": "heating",
        "name": "Heating",
        "device_class": "heat",
        "entity_category": None,
    },
    {
        "topic": "mos/charge",
        "name": "Charge MOS",
        "device_class": None,
        "entity_category": None,
    },
    {
        "topic": "mos/discharge",
        "name": "Discharge MOS",
        "device_class": None,
        "entity_category": None,
    },
    {
        "topic": "mos/precharge",
        "name": "Precharge",
        "device_class": None,
        "entity_category": None,
    },
    {
        "topic": "alarms",
        "name": "Alarms active",
        "device_class": "problem",
        "entity_category": None,
    },
)

# dynamic per-cell sensor templates keyed by the cell subtopic field
CELL_SENSOR_CATALOG = {
    "voltage": {
        "name": "Cell {index} voltage",
        "device_class": "voltage",
        "unit": "V",
        "state_class": "measurement",
        "entity_category": None,
    },
    "resistance": {
        "name": "Cell {index} resistance",
        "device_class": None,
        "unit": "Ω",
        "state_class": "measurement",
        "entity_category": None,
    },
}

# template for the 13 dynamic per-alarm binary sensors
ALARM_BINARY_CATALOG = {
    "name": "Alarm {slug}",
    "device_class": "problem",
    "entity_category": None,
}

# string topics consumed as device info, never entities
DEVICE_INFO_TOPICS = frozenset(
    {"device_name", "model", "sw_version", "hw_version", "serial"}
)
