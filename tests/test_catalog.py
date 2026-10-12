"""catalog completeness tests: every spec section 4 topic maps to an entity or ignore rule."""

import sys
import unittest
from pathlib import Path

# make the namespace package importable without homeassistant
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components"))

from jkbms_mqtt import const, topology  # noqa: e402

# spec section 4 table, suffixes below <prefix>/<name>/ (dynamic cell/alarm
# topics are expanded separately via const.MAX_CELLS and const.ALARM_SLUGS)
SPEC_STATIC_TOPICS = (
    "availability",
    "online",
    "voltage",
    "current",
    "power",
    "soc",
    "soh",
    "capacity_remaining",
    "capacity_nominal",
    "cycles",
    "runtime_s",
    "temperature/mos",
    "temperature/1",
    "temperature/2",
    "balancing",
    "heating",
    "mos/charge",
    "mos/discharge",
    "mos/precharge",
    "balancing_current",
    "heating_current",
    "alarms",
    "error_bitmask",
    "device_name",
    "model",
    "sw_version",
    "hw_version",
    "serial",
)

SPEC_ALARM_SLUGS = {
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
}

SENSOR_KEYS = {"topic", "name", "device_class", "unit", "state_class", "entity_category"}
BINARY_KEYS = {"topic", "name", "device_class", "entity_category"}

SENSOR_TOPICS = {entry["topic"] for entry in const.SENSOR_CATALOG}
BINARY_TOPICS = {entry["topic"] for entry in const.BINARY_SENSOR_CATALOG}
ENTITY_TOPICS = SENSOR_TOPICS | BINARY_TOPICS


def resolve_coverage(suffix):
    """how a spec topic is handled: entity catalog or explicit ignore rule."""
    if suffix == const.AVAILABILITY_TOPIC:
        return "availability"
    if suffix in const.DEVICE_INFO_TOPICS:
        return "device_info"
    if suffix in SENSOR_TOPICS:
        return "sensor"
    if suffix in BINARY_TOPICS:
        return "binary_sensor"
    return None


class ConstantTests(unittest.TestCase):
    def test_domain_and_prefix_constants(self):
        self.assertEqual(const.DOMAIN, "jkbms_mqtt")
        self.assertEqual(const.DEFAULT_PREFIX, "jkbms")
        self.assertEqual(const.CONF_PREFIX, "prefix")

    def test_max_cells(self):
        self.assertEqual(const.MAX_CELLS, 24)

    def test_alarm_slugs_match_spec(self):
        self.assertEqual(set(const.ALARM_SLUGS), SPEC_ALARM_SLUGS)
        self.assertEqual(len(const.ALARM_SLUGS), 13)
        self.assertEqual(len(set(const.ALARM_SLUGS)), 13)
        self.assertEqual(const.ALARM_SLUGS[0], "cell_undervoltage")
        self.assertEqual(const.ALARM_SLUGS[-1], "locked_mos")


class CatalogShapeTests(unittest.TestCase):
    def test_sensor_entries_have_required_keys(self):
        for entry in const.SENSOR_CATALOG:
            with self.subTest(topic=entry.get("topic")):
                self.assertEqual(set(entry), SENSOR_KEYS)
                self.assertTrue(entry["name"])
                self.assertTrue(entry["topic"])

    def test_binary_entries_have_required_keys(self):
        for entry in const.BINARY_SENSOR_CATALOG:
            with self.subTest(topic=entry.get("topic")):
                self.assertEqual(set(entry), BINARY_KEYS)
                self.assertTrue(entry["name"])
                self.assertTrue(entry["topic"])

    def test_topics_unique_per_catalog(self):
        self.assertEqual(len(SENSOR_TOPICS), len(const.SENSOR_CATALOG))
        self.assertEqual(len(BINARY_TOPICS), len(const.BINARY_SENSOR_CATALOG))

    def test_sensor_binary_overlap_is_only_alarms(self):
        # the csv topic feeds both the diagnostic sensor and the aggregate sensor
        self.assertEqual(SENSOR_TOPICS & BINARY_TOPICS, {"alarms"})

    def test_state_classes_valid(self):
        allowed = {None, "measurement", "total", "total_increasing"}
        for entry in const.SENSOR_CATALOG:
            with self.subTest(topic=entry["topic"]):
                self.assertIn(entry["state_class"], allowed)

    def test_entity_categories_valid(self):
        allowed = {None, "config", "diagnostic"}
        for entry in (*const.SENSOR_CATALOG, *const.BINARY_SENSOR_CATALOG):
            with self.subTest(topic=entry["topic"]):
                self.assertIn(entry["entity_category"], allowed)

    def test_binary_device_classes_valid(self):
        allowed = {None, "battery_charging", "heat", "problem"}
        for entry in const.BINARY_SENSOR_CATALOG:
            with self.subTest(topic=entry["topic"]):
                self.assertIn(entry["device_class"], allowed)

    def test_cell_template_kinds(self):
        self.assertEqual(set(const.CELL_SENSOR_CATALOG), {"voltage", "resistance"})
        for kind, entry in const.CELL_SENSOR_CATALOG.items():
            with self.subTest(kind=kind):
                self.assertEqual(set(entry), SENSOR_KEYS - {"topic"})
                self.assertIn("{index}", entry["name"])

    def test_alarm_template(self):
        self.assertEqual(const.ALARM_BINARY_CATALOG["device_class"], "problem")
        self.assertIn("{slug}", const.ALARM_BINARY_CATALOG["name"])


class CatalogContentTests(unittest.TestCase):
    def test_key_sensor_rows_match_spec(self):
        by_topic = {entry["topic"]: entry for entry in const.SENSOR_CATALOG}
        self.assertEqual(by_topic["voltage"]["device_class"], "voltage")
        self.assertEqual(by_topic["voltage"]["unit"], "V")
        self.assertEqual(by_topic["soc"]["device_class"], "battery")
        self.assertEqual(by_topic["soc"]["unit"], "%")
        self.assertIsNone(by_topic["capacity_nominal"]["device_class"])
        self.assertEqual(by_topic["capacity_nominal"]["unit"], "Ah")
        self.assertEqual(by_topic["cycles"]["state_class"], "total_increasing")
        self.assertEqual(by_topic["cycles"]["unit"], "cycles")
        self.assertEqual(by_topic["runtime_s"]["device_class"], "duration")
        self.assertEqual(by_topic["runtime_s"]["state_class"], "total_increasing")
        self.assertEqual(by_topic["temperature/mos"]["device_class"], "temperature")
        self.assertEqual(by_topic["temperature/mos"]["unit"], "°C")
        self.assertEqual(by_topic["online"]["device_class"], "timestamp")
        self.assertEqual(by_topic["online"]["entity_category"], "diagnostic")

    def test_diagnostic_entities(self):
        by_topic = {entry["topic"]: entry for entry in const.SENSOR_CATALOG}
        for topic in ("online", "error_bitmask", "alarms"):
            with self.subTest(topic=topic):
                self.assertEqual(by_topic[topic]["entity_category"], "diagnostic")

    def test_key_binary_rows_match_spec(self):
        by_topic = {entry["topic"]: entry for entry in const.BINARY_SENSOR_CATALOG}
        self.assertEqual(by_topic["balancing"]["device_class"], "battery_charging")
        self.assertEqual(by_topic["heating"]["device_class"], "heat")
        self.assertEqual(by_topic["alarms"]["device_class"], "problem")
        self.assertIsNone(by_topic["mos/charge"]["device_class"])
        self.assertIsNone(by_topic["mos/discharge"]["device_class"])
        self.assertIsNone(by_topic["mos/precharge"]["device_class"])


class CoverageTests(unittest.TestCase):
    def test_every_static_spec_topic_is_covered(self):
        for suffix in SPEC_STATIC_TOPICS:
            with self.subTest(topic=suffix):
                coverage = resolve_coverage(suffix)
                self.assertIsNotNone(coverage, f"unhandled spec topic {suffix!r}")

    def test_availability_is_explicit_ignore_rule(self):
        # device-wide availability, never an entity
        self.assertNotIn("availability", ENTITY_TOPICS)
        self.assertEqual(const.AVAILABILITY_TOPIC, "availability")

    def test_device_info_topics_are_explicit_ignore_rule(self):
        self.assertEqual(
            const.DEVICE_INFO_TOPICS,
            {"device_name", "model", "sw_version", "hw_version", "serial"},
        )
        self.assertFalse(const.DEVICE_INFO_TOPICS & ENTITY_TOPICS)

    def test_every_cell_topic_covered(self):
        for index in range(1, const.MAX_CELLS + 1):
            for kind in const.CELL_SENSOR_CATALOG:
                field = ("cell", str(index), kind)
                with self.subTest(field=field):
                    self.assertTrue(topology.is_cell_topic(field))
                    self.assertEqual(topology.cell_index(field), index)
                    self.assertIn(kind, const.CELL_SENSOR_CATALOG)

    def test_out_of_range_cells_not_classified(self):
        self.assertFalse(topology.is_cell_topic(("cell", "0", "voltage")))
        self.assertFalse(
            topology.is_cell_topic(("cell", str(const.MAX_CELLS + 1), "resistance"))
        )

    def test_every_alarm_topic_covered(self):
        for slug in const.ALARM_SLUGS:
            field = ("alarm", slug)
            with self.subTest(slug=slug):
                self.assertTrue(topology.is_alarm_topic(field))
                self.assertEqual(topology.alarm_slug(field), slug)
                self.assertEqual(
                    const.ALARM_BINARY_CATALOG["device_class"], "problem"
                )

    def test_no_invented_static_catalog_topics(self):
        # reverse completeness: every catalog entry must appear in the spec table
        for suffix in ENTITY_TOPICS:
            with self.subTest(topic=suffix):
                self.assertIn(suffix, SPEC_STATIC_TOPICS)

    def test_static_temperature_topics_classified(self):
        for suffix in ("temperature/mos", "temperature/1", "temperature/2"):
            with self.subTest(topic=suffix):
                field = tuple(suffix.split("/"))
                self.assertTrue(topology.is_temperature_topic(field))


if __name__ == "__main__":
    unittest.main()
