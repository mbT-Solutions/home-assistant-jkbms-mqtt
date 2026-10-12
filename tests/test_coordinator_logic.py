"""pure routing decision tests for coordinator.parse_message; stdlib only, no homeassistant."""

import sys
import unittest
from pathlib import Path

# make the package importable without homeassistant
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))

from jkbms_mqtt import const, coordinator, topology  # noqa: e402


class KindConstantsTests(unittest.TestCase):
    def test_kind_constant_values(self):
        self.assertEqual(
            {coordinator.KIND_VALUE, coordinator.KIND_AVAILABILITY,
             coordinator.KIND_INFO, coordinator.KIND_UNKNOWN},
            {"value", "availability", "info", "unknown"},
        )


class ParseMessageTests(unittest.TestCase):
    def test_value_topic(self):
        decision = coordinator.parse_message("jkbms/bms1/voltage", "54.028", "jkbms")
        self.assertEqual(decision.device, "bms1")
        self.assertEqual(decision.field, ("voltage",))
        self.assertEqual(decision.kind, coordinator.KIND_VALUE)

    def test_nested_value_topic(self):
        decision = coordinator.parse_message(
            "jkbms/bms1/cell/3/voltage", "3.381", "jkbms"
        )
        self.assertEqual(decision.device, "bms1")
        self.assertEqual(decision.field, ("cell", "3", "voltage"))
        self.assertEqual(decision.kind, coordinator.KIND_VALUE)

    def test_alarm_topic_is_value(self):
        decision = coordinator.parse_message(
            "jkbms/bms1/alarm/short_circuit", "1", "jkbms"
        )
        self.assertEqual(decision.field, ("alarm", "short_circuit"))
        self.assertEqual(decision.kind, coordinator.KIND_VALUE)

    def test_unknown_value_topic_still_routes_as_value(self):
        # forward compatibility: bridge may add topics the catalog does not know
        decision = coordinator.parse_message("jkbms/bms1/foo", "1", "jkbms")
        self.assertEqual(decision.device, "bms1")
        self.assertEqual(decision.field, ("foo",))
        self.assertEqual(decision.kind, coordinator.KIND_VALUE)

    def test_availability_topic(self):
        for payload in ("online", "offline", "garbage"):
            with self.subTest(payload=payload):
                decision = coordinator.parse_message(
                    "jkbms/bms1/availability", payload, "jkbms"
                )
                self.assertEqual(decision.device, "bms1")
                self.assertEqual(decision.field, ("availability",))
                self.assertEqual(decision.kind, coordinator.KIND_AVAILABILITY)

    def test_device_info_topics(self):
        for topic in sorted(const.DEVICE_INFO_TOPICS):
            with self.subTest(topic=topic):
                decision = coordinator.parse_message(
                    f"jkbms/bms1/{topic}", "value", "jkbms"
                )
                self.assertEqual(decision.device, "bms1")
                self.assertEqual(decision.field, (topic,))
                self.assertEqual(decision.kind, coordinator.KIND_INFO)

    def test_empty_device_segment_is_unknown(self):
        decision = coordinator.parse_message("jkbms//voltage", "1", "jkbms")
        self.assertEqual(decision.kind, coordinator.KIND_UNKNOWN)

    def test_empty_field_segment_is_unknown(self):
        decision = coordinator.parse_message("jkbms/bms1/", "1", "jkbms")
        self.assertEqual(decision.device, "bms1")
        self.assertEqual(decision.kind, coordinator.KIND_UNKNOWN)

    def test_reserved_bridge_root_ignored(self):
        for topic in ("jkbms/bridge/status", "jkbms/bridge"):
            with self.subTest(topic=topic):
                self.assertIsNone(coordinator.parse_message(topic, "1", "jkbms"))

    def test_wrong_prefix_ignored(self):
        for prefix in ("other", "jkbms2", "jk"):
            with self.subTest(prefix=prefix):
                self.assertIsNone(
                    coordinator.parse_message("jkbms/bms1/voltage", "1", prefix)
                )

    def test_topic_without_device_or_field_ignored(self):
        self.assertIsNone(coordinator.parse_message("jkbms", "1", "jkbms"))
        self.assertIsNone(coordinator.parse_message("jkbms/bms1", "1", "jkbms"))
        self.assertIsNone(coordinator.parse_message("", "1", "jkbms"))
        self.assertIsNone(coordinator.parse_message(None, "1", "jkbms"))

    def test_multisegment_prefix(self):
        decision = coordinator.parse_message(
            "home/jkbms/bms1/voltage", "1", "home/jkbms"
        )
        self.assertEqual(decision.device, "bms1")
        self.assertEqual(decision.field, ("voltage",))
        self.assertEqual(decision.kind, coordinator.KIND_VALUE)
        self.assertIsNone(
            coordinator.parse_message("jkbms/bms1/voltage", "1", "home/jkbms")
        )

    def test_prefix_sanitized_before_routing(self):
        # separators and wildcards are stripped from the configured prefix
        decision = coordinator.parse_message(
            "jkbms/bms1/voltage", "1", " jkbms/ "
        )
        self.assertEqual(decision.kind, coordinator.KIND_VALUE)
        for prefix in ("jb+ms", "home/other"):
            with self.subTest(prefix=prefix):
                self.assertIsNone(
                    coordinator.parse_message("jkbms/bms1/voltage", "1", prefix)
                )

    def test_payload_never_changes_routing(self):
        base = ("bms1", ("voltage",), coordinator.KIND_VALUE)
        for payload in ("", "1", None, "0x00000000", "a,b,c"):
            with self.subTest(payload=payload):
                decision = coordinator.parse_message(
                    "jkbms/bms1/voltage", payload, "jkbms"
                )
                self.assertEqual(
                    (decision.device, decision.field, decision.kind), base
                )


class SplitTopicAgreementTests(unittest.TestCase):
    def test_parse_message_agrees_with_split_topic(self):
        for topic in (
            "jkbms/bms1/voltage",
            "jkbms/bms1/temperature/mos",
            "jkbms/bms1/alarm/ic_error",
            "jkbms/bms1/cell/24/resistance",
        ):
            with self.subTest(topic=topic):
                split = topology.split_topic(topic, "jkbms")
                decision = coordinator.parse_message(topic, "1", "jkbms")
                self.assertEqual((decision.device, decision.field), split)


if __name__ == "__main__":
    unittest.main()
