"""unit tests for topic sanitizing, parsing and field classification."""

import sys
import unittest
from pathlib import Path

# make the namespace package importable without homeassistant
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))

from jkbms_mqtt import const, topology  # noqa: e402


class SanitizeSegmentTests(unittest.TestCase):
    def test_plain_segment_unchanged(self):
        self.assertEqual(topology.sanitize_segment("bat"), "bat")

    def test_strips_nul(self):
        self.assertEqual(topology.sanitize_segment("ba\x00t"), "bat")

    def test_strips_wildcards(self):
        self.assertEqual(topology.sanitize_segment("a+b"), "ab")
        self.assertEqual(topology.sanitize_segment("a#b"), "ab")

    def test_strips_slash_inside_segment(self):
        self.assertEqual(topology.sanitize_segment("a/b"), "ab")

    def test_trims_whitespace(self):
        self.assertEqual(topology.sanitize_segment("  name \t"), "name")

    def test_caps_at_100(self):
        self.assertEqual(topology.sanitize_segment("x" * 150), "x" * 100)

    def test_empty_variants_return_none(self):
        for value in ("", "   ", "+#", "\x00", " \x00 "):
            with self.subTest(value=repr(value)):
                self.assertIsNone(topology.sanitize_segment(value))

    def test_none_returns_none(self):
        self.assertIsNone(topology.sanitize_segment(None))


class SanitizePrefixTests(unittest.TestCase):
    def test_plain_prefix_unchanged(self):
        self.assertEqual(topology.sanitize_prefix("jkbms"), "jkbms")

    def test_empty_falls_back_to_default(self):
        self.assertEqual(topology.sanitize_prefix(""), const.DEFAULT_PREFIX)
        self.assertEqual(topology.sanitize_prefix("   "), const.DEFAULT_PREFIX)
        self.assertEqual(topology.sanitize_prefix("///"), const.DEFAULT_PREFIX)
        self.assertEqual(topology.sanitize_prefix(None), const.DEFAULT_PREFIX)

    def test_multi_segment_with_wildcard_and_space(self):
        # spec: strip '+' then trim -> third segment becomes 'x'
        self.assertEqual(topology.sanitize_prefix("home/bat/+ x"), "home/bat/x")

    def test_multi_segment_trims_each_segment(self):
        self.assertEqual(topology.sanitize_prefix("  home / bat  "), "home/bat")

    def test_drops_empty_segments(self):
        self.assertEqual(topology.sanitize_prefix("home//bat"), "home/bat")

    def test_only_forbidden_chars_falls_back_to_default(self):
        self.assertEqual(topology.sanitize_prefix("++/##"), const.DEFAULT_PREFIX)

    def test_caps_each_segment_at_100(self):
        prefix = topology.sanitize_prefix("a" * 150 + "/" + "b" * 150)
        self.assertEqual(prefix, "a" * 100 + "/" + "b" * 100)

    def test_nul_and_wildcard_mixed(self):
        self.assertEqual(topology.sanitize_prefix("home/\x00bat/#x+"), "home/bat/x")


class SplitTopicTests(unittest.TestCase):
    PREFIX = "jkbms"

    def test_simple_field(self):
        self.assertEqual(
            topology.split_topic("jkbms/name/voltage", self.PREFIX),
            ("name", ("voltage",)),
        )

    def test_cell_field(self):
        self.assertEqual(
            topology.split_topic("jkbms/name/cell/3/voltage", self.PREFIX),
            ("name", ("cell", "3", "voltage")),
        )

    def test_alarm_field(self):
        self.assertEqual(
            topology.split_topic("jkbms/name/alarm/ic_error", self.PREFIX),
            ("name", ("alarm", "ic_error")),
        )

    def test_temperature_field(self):
        self.assertEqual(
            topology.split_topic("jkbms/name/temperature/2", self.PREFIX),
            ("name", ("temperature", "2")),
        )

    def test_device_availability_is_a_field(self):
        self.assertEqual(
            topology.split_topic("jkbms/name/availability", self.PREFIX),
            ("name", ("availability",)),
        )

    def test_bridge_availability_excluded(self):
        self.assertIsNone(
            topology.split_topic("jkbms/bridge/availability", self.PREFIX)
        )

    def test_bridge_root_reserved(self):
        self.assertIsNone(topology.split_topic("jkbms/bridge/uptime", self.PREFIX))
        self.assertIsNone(topology.split_topic("jkbms/bridge/a/b", self.PREFIX))

    def test_wrong_prefix_returns_none(self):
        self.assertIsNone(topology.split_topic("other/name/voltage", self.PREFIX))

    def test_prefix_must_match_full_segments(self):
        self.assertIsNone(topology.split_topic("jkbms2/name/voltage", self.PREFIX))

    def test_multi_segment_prefix(self):
        self.assertEqual(
            topology.split_topic("home/bat/name/voltage", "home/bat"),
            ("name", ("voltage",)),
        )

    def test_multi_segment_prefix_wrong_suffix(self):
        self.assertIsNone(topology.split_topic("home/bat/name/voltage", "home/bat/x"))
        self.assertIsNone(topology.split_topic("home/x/name/voltage", "home/bat"))

    def test_prefix_sanitized_before_matching(self):
        self.assertEqual(
            topology.split_topic("home/bat/name/voltage", " home/bat "),
            ("name", ("voltage",)),
        )

    def test_missing_field_returns_none(self):
        self.assertIsNone(topology.split_topic("jkbms/name", self.PREFIX))
        self.assertIsNone(topology.split_topic("jkbms", self.PREFIX))

    def test_empty_topic_returns_none(self):
        self.assertIsNone(topology.split_topic("", self.PREFIX))

    def test_empty_prefix_falls_back_to_default(self):
        self.assertEqual(
            topology.split_topic("jkbms/name/voltage", ""),
            ("name", ("voltage",)),
        )


class CellTopicTests(unittest.TestCase):
    def test_valid_kinds(self):
        self.assertTrue(topology.is_cell_topic(("cell", "1", "voltage")))
        self.assertTrue(topology.is_cell_topic(("cell", "24", "resistance")))

    def test_index_bounds(self):
        self.assertFalse(topology.is_cell_topic(("cell", "0", "voltage")))
        self.assertFalse(topology.is_cell_topic(("cell", "25", "voltage")))

    def test_unknown_kind_rejected(self):
        self.assertFalse(topology.is_cell_topic(("cell", "3", "temperature")))

    def test_wrong_shape_rejected(self):
        self.assertFalse(topology.is_cell_topic(("cell", "3")))
        self.assertFalse(topology.is_cell_topic(("cell", "3", "voltage", "x")))
        self.assertFalse(topology.is_cell_topic(("cells", "3", "voltage")))

    def test_non_numeric_index_rejected(self):
        self.assertFalse(topology.is_cell_topic(("cell", "3a", "voltage")))

    def test_cell_index(self):
        self.assertEqual(topology.cell_index(("cell", "7", "voltage")), 7)
        self.assertIsNone(topology.cell_index(("cell", "x", "voltage")))


class AlarmTopicTests(unittest.TestCase):
    def test_known_slug(self):
        self.assertTrue(topology.is_alarm_topic(("alarm", "ic_error")))
        self.assertEqual(topology.alarm_slug(("alarm", "locked_mos")), "locked_mos")

    def test_unknown_slug_rejected(self):
        self.assertFalse(topology.is_alarm_topic(("alarm", "unknown_alarm")))

    def test_wrong_shape_rejected(self):
        self.assertFalse(topology.is_alarm_topic(("alarm",)))
        self.assertFalse(topology.is_alarm_topic(("alarm", "ic_error", "x")))
        self.assertFalse(topology.is_alarm_topic(("alarms", "ic_error")))


class TemperatureTopicTests(unittest.TestCase):
    def test_numbered_probe(self):
        self.assertTrue(topology.is_temperature_topic(("temperature", "2")))
        self.assertEqual(
            topology.temperature_probe(("temperature", "2")),
            "2",
        )

    def test_mos_probe(self):
        self.assertTrue(topology.is_temperature_topic(("temperature", "mos")))
        self.assertEqual(
            topology.temperature_probe(("temperature", "mos")),
            "mos",
        )

    def test_zero_probe_rejected(self):
        self.assertFalse(topology.is_temperature_topic(("temperature", "0")))

    def test_non_numeric_probe_rejected(self):
        self.assertFalse(topology.is_temperature_topic(("temperature", "x")))

    def test_wrong_shape_rejected(self):
        self.assertFalse(topology.is_temperature_topic(("temperature",)))
        self.assertFalse(topology.is_temperature_topic(("temperature", "1", "x")))

    def test_first_probe_valid(self):
        self.assertTrue(topology.is_temperature_topic(("temperature", "1")))


if __name__ == "__main__":
    unittest.main()
