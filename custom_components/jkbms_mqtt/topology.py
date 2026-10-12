"""pure topic <-> (device, field) parsing and prefix sanitizing; stdlib only."""

from .const import ALARM_SLUGS, DEFAULT_PREFIX, MAX_CELLS

# nul and mqtt wildcards/separators are forbidden inside a segment
_FORBIDDEN_CHARS = ("\x00", "/", "+", "#")
_MAX_SEGMENT_LENGTH = 100

# roots below <prefix>/ reserved for bridge-internal topics, never devices
RESERVED_ROOTS = frozenset({"bridge"})

_CELL_FIELDS = frozenset({"voltage", "resistance"})


def sanitize_segment(segment):
    """strip forbidden chars, trim, cap at 100 chars; none when nothing remains."""
    if not segment:
        return None
    for char in _FORBIDDEN_CHARS:
        segment = segment.replace(char, "")
    segment = segment.strip()
    if not segment:
        return None
    return segment[:_MAX_SEGMENT_LENGTH]


def sanitize_prefix(prefix):
    """sanitize each '/'-separated segment and rejoin; default prefix when empty."""
    if prefix is None:
        return DEFAULT_PREFIX
    segments = [
        segment
        for segment in (sanitize_segment(part) for part in prefix.split("/"))
        if segment
    ]
    if not segments:
        return DEFAULT_PREFIX
    return "/".join(segments)


def split_topic(topic, prefix):
    """split a topic into (device_name, field_path); none when unrelated or reserved.

    prefix is sanitized first, so raw config values are accepted.
    """
    prefix = sanitize_prefix(prefix)
    if not topic:
        return None
    parts = topic.split("/")
    prefix_parts = prefix.split("/")
    if len(parts) <= len(prefix_parts):
        return None
    if parts[: len(prefix_parts)] != prefix_parts:
        return None
    device = parts[len(prefix_parts)]
    if device in RESERVED_ROOTS:
        return None
    field = tuple(parts[len(prefix_parts) + 1 :])
    if not field:
        return None
    return device, field


def cell_index(field):
    """cell index within 1..max_cells when field is a cell topic, else none."""
    if len(field) != 3 or field[0] != "cell" or field[2] not in _CELL_FIELDS:
        return None
    if not field[1].isdigit():
        return None
    index = int(field[1])
    if not 1 <= index <= MAX_CELLS:
        return None
    return index


def is_cell_topic(field):
    return cell_index(field) is not None


def alarm_slug(field):
    """slug when field addresses one of the known alarms, else none."""
    if len(field) == 2 and field[0] == "alarm" and field[1] in ALARM_SLUGS:
        return field[1]
    return None


def is_alarm_topic(field):
    return alarm_slug(field) is not None


def temperature_probe(field):
    """probe key 'mos' or the numeric index string for valid temperature topics."""
    if len(field) == 2 and field[0] == "temperature":
        probe = field[1]
        if probe == "mos":
            return probe
        if probe.isdigit() and int(probe) >= 1:
            return probe
    return None


def is_temperature_topic(field):
    return temperature_probe(field) is not None
