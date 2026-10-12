"""pure payload -> state coercion helpers; stdlib only, no homeassistant imports."""

import re
from datetime import datetime, timezone

# the bridge formats plain fixed-decimal numbers, never scientific notation
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_DISALLOWED_RE = re.compile(r"[^a-z0-9_]+")
_UNDERSCORE_RUN_RE = re.compile(r"_+")


def to_float(text):
    """float for plain decimal strings, none on garbage."""
    if not isinstance(text, str) or not _FLOAT_RE.match(text):
        return None
    return float(text)


def to_flag(text):
    """true for '1', false for '0', none otherwise."""
    if text == "1":
        return True
    if text == "0":
        return False
    return None


def alarm_payload(text):
    """true only for payload '1'; empty or any other payload means cleared."""
    return text == "1"


def alarms_csv_active(text):
    """true when the csv holds at least one slug after stripping."""
    if not isinstance(text, str):
        return False
    return bool(text.strip())


def epoch_to_datetime(seconds_text):
    """timezone-aware utc datetime from epoch seconds text, none on garbage."""
    if not isinstance(seconds_text, str) or not _INT_RE.match(seconds_text):
        return None
    try:
        return datetime.fromtimestamp(int(seconds_text), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _slugify(text):
    slug = text.lower()
    slug = _DISALLOWED_RE.sub("_", slug)
    slug = _UNDERSCORE_RUN_RE.sub("_", slug)
    return slug.strip("_")


def unique_id_for(device_name, field):
    """stable lowercase slug surviving ha entity_id rules."""
    return _slugify("_".join((device_name, *field)))


def device_registry_name(friendly_from_topic, device_name_topic_value):
    """device_name topic value wins when non-empty, else the topic name."""
    if isinstance(device_name_topic_value, str) and device_name_topic_value.strip():
        return device_name_topic_value.strip()
    return friendly_from_topic
