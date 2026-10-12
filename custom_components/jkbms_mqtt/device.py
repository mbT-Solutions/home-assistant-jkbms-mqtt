"""per-device state: topic name, string values, online flag.
pure data, no homeassistant imports.
"""

from dataclasses import dataclass, field

from .const import DEVICE_INFO_TOPICS, DOMAIN
from .payloads import device_registry_name

MANUFACTURER = "JK BMS"
DEFAULT_MODEL = "JK BMS"

# registry fields device_info can carry; used by changed_info_fields
_INFO_FIELDS = (
    "name",
    "manufacturer",
    "model",
    "sw_version",
    "hw_version",
    "serial_number",
)


@dataclass
class JkbmsDevice:
    """one bms discovered under the prefix."""

    name: str
    online: bool = False
    string_values: dict = field(default_factory=dict)

    def set_string(self, topic, value):
        """record a device info string topic payload; unknown topics ignored."""
        if topic not in DEVICE_INFO_TOPICS:
            return
        self.string_values[topic] = value

    def device_info(self):
        """dict usable as homeassistant deviceinfo kwargs."""
        info = {
            "identifiers": {(DOMAIN, self.name)},
            "name": device_registry_name(
                self.name, self.string_values.get("device_name")
            ),
            "manufacturer": MANUFACTURER,
            "model": self.string_values.get("model") or DEFAULT_MODEL,
        }
        # mqtt topic "serial" maps to ha deviceinfo field serial_number
        for topic, key in (
            ("sw_version", "sw_version"),
            ("hw_version", "hw_version"),
            ("serial", "serial_number"),
        ):
            value = self.string_values.get(topic)
            if value:
                info[key] = value
        return info


def changed_info_fields(device, current):
    """registry fields whose value differs from the current device entry.

    current maps registry field -> present value (none when absent);
    fields without a value in device_info are never touched.
    """
    info = device.device_info()
    return {
        key: info[key]
        for key in _INFO_FIELDS
        if key in info and info[key] != current.get(key)
    }
