"""payload coercion and device info tests: every helper incl edge cases."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

# make the namespace package importable without homeassistant
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))

from jkbms_mqtt import payloads  # noqa: e402
from jkbms_mqtt.device import JkbmsDevice, changed_info_fields  # noqa: e402


class ToFloatTests(unittest.TestCase):
    def test_plain_decimals(self):
        self.assertEqual(payloads.to_float("54.028"), 54.028)
        self.assertEqual(payloads.to_float("-0.727"), -0.727)

    def test_zero_and_int_like(self):
        self.assertEqual(payloads.to_float("0"), 0.0)
        self.assertEqual(payloads.to_float("12"), 12.0)
        self.assertEqual(payloads.to_float("-39.3"), -39.3)

    def test_garbage_returns_none(self):
        for text in ("", "abc", "nan", "inf", "1e3", "1,5", " 1.5", "1.5 ", None, 54):
            with self.subTest(text=text):
                self.assertIsNone(payloads.to_float(text))


class ToFlagTests(unittest.TestCase):
    def test_one_and_zero(self):
        self.assertIs(payloads.to_flag("1"), True)
        self.assertIs(payloads.to_flag("0"), False)

    def test_garbage_returns_none(self):
        for text in ("", "x", "01", "1 ", " 1", "true", None):
            with self.subTest(text=text):
                self.assertIsNone(payloads.to_flag(text))


class AlarmPayloadTests(unittest.TestCase):
    def test_one_is_active(self):
        self.assertIs(payloads.alarm_payload("1"), True)

    def test_empty_clears(self):
        self.assertIs(payloads.alarm_payload(""), False)

    def test_anything_else_clears(self):
        for text in ("0", "x", "true", None):
            with self.subTest(text=text):
                self.assertIs(payloads.alarm_payload(text), False)


class AlarmsCsvActiveTests(unittest.TestCase):
    def test_multi_slug_csv(self):
        self.assertIs(payloads.alarms_csv_active("cell_undervoltage,ic_error"), True)

    def test_single_slug_csv(self):
        self.assertIs(payloads.alarms_csv_active("cell_undervoltage"), True)

    def test_empty_or_blank_inactive(self):
        for text in ("", "   ", "\t"):
            with self.subTest(text=text):
                self.assertIs(payloads.alarms_csv_active(text), False)


class EpochToDatetimeTests(unittest.TestCase):
    def test_known_epoch_exact(self):
        self.assertEqual(
            payloads.epoch_to_datetime("1757000000"),
            datetime(2025, 9, 4, 15, 33, 20, tzinfo=timezone.utc),
        )

    def test_result_is_utc_aware(self):
        value = payloads.epoch_to_datetime("0")
        self.assertIsNotNone(value.tzinfo)
        self.assertEqual(value.utcoffset().total_seconds(), 0)
        self.assertEqual(value, datetime(1970, 1, 1, tzinfo=timezone.utc))

    def test_garbage_returns_none(self):
        for text in ("", "abc", "1e3", "1757000000.5", " 12", None, 1757000000):
            with self.subTest(text=text):
                self.assertIsNone(payloads.epoch_to_datetime(text))


class UniqueIdTests(unittest.TestCase):
    def test_stable(self):
        for field in (("cell", "3", "voltage"), ("mos", "charge"), ("alarm", "ic_error")):
            with self.subTest(field=field):
                first = payloads.unique_id_for("Battery X", field)
                second = payloads.unique_id_for("Battery X", field)
                self.assertEqual(first, second)

    def test_space_differs_from_no_space(self):
        self.assertNotEqual(
            payloads.unique_id_for("Battery X", ("voltage",)),
            payloads.unique_id_for("BatteryX", ("voltage",)),
        )

    def test_cell_field_shape(self):
        self.assertEqual(
            payloads.unique_id_for("Battery X", ("cell", "3", "voltage")),
            "battery_x_cell_3_voltage",
        )

    def test_mos_field_shape(self):
        self.assertEqual(
            payloads.unique_id_for("Battery X", ("mos", "charge")),
            "battery_x_mos_charge",
        )

    def test_alarm_field_shape(self):
        self.assertEqual(
            payloads.unique_id_for("TESTBMS00000001", ("alarm", "ic_error")),
            "testbms00000001_alarm_ic_error",
        )

    def test_uppercase_name_lowercased(self):
        self.assertEqual(
            payloads.unique_id_for("BATTERY", ("voltage",)),
            "battery_voltage",
        )

    def test_disallowed_chars_and_repeats_collapse(self):
        self.assertEqual(
            payloads.unique_id_for("Battery  #1 (Garage)", ("voltage",)),
            "battery_1_garage_voltage",
        )
        self.assertEqual(
            payloads.unique_id_for("A__B--C", ("voltage",)),
            "a_b_c_voltage",
        )

    def test_edge_underscores_stripped(self):
        self.assertEqual(payloads.unique_id_for("-X-", ("voltage",)), "x_voltage")

    def test_only_entity_id_chars_remain(self):
        self.assertRegex(
            payloads.unique_id_for("Battery X", ("cell", "12", "resistance")),
            r"^[a-z0-9_]+$",
        )


class DeviceRegistryNameTests(unittest.TestCase):
    def test_topic_value_wins(self):
        self.assertEqual(payloads.device_registry_name("bat1", "My Battery"), "My Battery")

    def test_empty_value_falls_back_to_topic_name(self):
        self.assertEqual(payloads.device_registry_name("bat1", ""), "bat1")

    def test_blank_value_falls_back_to_topic_name(self):
        self.assertEqual(payloads.device_registry_name("bat1", "   "), "bat1")

    def test_missing_value_falls_back_to_topic_name(self):
        self.assertEqual(payloads.device_registry_name("bat1", None), "bat1")


class JkbmsDeviceInfoTests(unittest.TestCase):
    def test_defaults_and_name_fallback(self):
        device = JkbmsDevice(name="bat1")
        self.assertFalse(device.online)
        self.assertEqual(device.string_values, {})
        info = device.device_info()
        self.assertEqual(info["identifiers"], {("jkbms_mqtt", "bat1")})
        self.assertEqual(info["name"], "bat1")
        self.assertEqual(info["manufacturer"], "JK BMS")
        self.assertEqual(info["model"], "JK BMS")
        self.assertNotIn("sw_version", info)
        self.assertNotIn("hw_version", info)
        self.assertNotIn("serial_number", info)

    def test_device_name_topic_wins(self):
        device = JkbmsDevice(name="TESTBMS00000001")
        device.set_string("device_name", "My Battery")
        self.assertEqual(device.device_info()["name"], "My Battery")

    def test_string_topics_fill_info(self):
        device = JkbmsDevice(name="TESTBMS00000001")
        device.set_string("model", "JK-PB2A16S20P")
        device.set_string("sw_version", "19.27")
        device.set_string("hw_version", "19A")
        device.set_string("serial", "TESTBMS00000001")
        device.online = True
        self.assertTrue(device.online)
        info = device.device_info()
        self.assertEqual(info["model"], "JK-PB2A16S20P")
        self.assertEqual(info["manufacturer"], "JK BMS")
        self.assertEqual(info["sw_version"], "19.27")
        self.assertEqual(info["hw_version"], "19A")
        self.assertEqual(info["serial_number"], "TESTBMS00000001")

    def test_empty_string_topics_omitted(self):
        device = JkbmsDevice(name="bat1")
        device.set_string("sw_version", "")
        device.set_string("serial", "")
        info = device.device_info()
        self.assertNotIn("sw_version", info)
        self.assertNotIn("serial_number", info)
        self.assertEqual(info["model"], "JK BMS")

    def test_unknown_string_topics_ignored(self):
        device = JkbmsDevice(name="bat1")
        device.set_string("voltage", "54.028")
        self.assertEqual(device.string_values, {})

    def test_changed_info_fields_full_diff(self):
        device = JkbmsDevice(name="bat1")
        device.set_string("device_name", "My Battery")
        device.set_string("model", "JK-PB2A16S20P")
        device.set_string("sw_version", "19.27")
        device.set_string("hw_version", "19A")
        device.set_string("serial", "TESTBMS00000001")
        current = {
            "name": "bat1",
            "manufacturer": "JK BMS",
            "model": "JK BMS",
            "sw_version": None,
            "hw_version": None,
            "serial_number": None,
        }
        self.assertEqual(
            changed_info_fields(device, current),
            {
                "name": "My Battery",
                "model": "JK-PB2A16S20P",
                "sw_version": "19.27",
                "hw_version": "19A",
                "serial_number": "TESTBMS00000001",
            },
        )

    def test_changed_info_fields_no_diff_no_changes(self):
        device = JkbmsDevice(name="bat1")
        device.set_string("model", "JK-PB2A16S20P")
        current = {
            "name": "bat1",
            "manufacturer": "JK BMS",
            "model": "JK-PB2A16S20P",
            "sw_version": "19.27",
            "hw_version": None,
            "serial_number": None,
        }
        self.assertEqual(changed_info_fields(device, current), {})

    def test_changed_info_fields_never_clears_absent_fields(self):
        # sw_version unknown on the device: absent from device_info, so it
        # must not be overwritten even though the registry has a value
        device = JkbmsDevice(name="bat1")
        current = {
            "name": "bat1",
            "manufacturer": "JK BMS",
            "model": "JK BMS",
            "sw_version": "19.27",
            "hw_version": None,
            "serial_number": None,
        }
        self.assertEqual(changed_info_fields(device, current), {})


if __name__ == "__main__":
    unittest.main()
