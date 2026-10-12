# Specification - home-assistant-jkbms-mqtt

## 1. Purpose

A Home Assistant integration ("the integration", domain `jkbms_mqtt`)
that exposes JK-BMS battery systems published by the android-jkbms-mqtt
bridge as Home Assistant devices: sensors, binary sensors and device
metadata. The bridge publishes per-value MQTT topics under a
**configurable prefix** (default `jkbms`); the integration subscribes,
creates one HA device per discovered BMS, and maps every topic to a
typed entity. No discovery messages are published by the bridge — the
integration actively listens (same pattern as `goecharger_mqtt`).

## 2. Requirements

### 2.1 Functional

| # | Requirement |
|---|-------------|
| F1 | Consume the bridge's per-value MQTT topics (android Spec.md §5.2) over the HA `mqtt` integration's broker connection |
| F2 | Topic prefix is configurable per config entry (default `jkbms`); multi-segment prefixes supported |
| F3 | Auto-discover one HA device per `<name>` seen under the prefix; entities appear as their topics arrive |
| F4 | Full entity catalog: pack sensors, dynamic per-cell voltage/resistance (max 24), binary sensors for MOS/balancing/heating, one binary sensor per known alarm plus an aggregate alarm sensor |
| F5 | Device availability from `<prefix>/<name>/availability` (online/offline) applies to all entities of the device |
| F6 | Device info (model, sw, hw, serial, device name) from the string topics; falls back to the topic name |
| F7 | Prefix changes via Options Flow without re-adding the integration |

### 2.2 Non-functional

| # | Requirement |
|---|-------------|
| N1 | Runs on Home Assistant ≥ 2026.8 (dev/test image `madebytimo/home-assistant`, HA 2026.8.3) |
| N2 | Custom integration installable via HACS-style `custom_components/jkbms_mqtt/`; no compile step |
| N3 | Zero runtime requirements beyond Home Assistant core + its `mqtt` integration (stdlib + HA core APIs only) |
| N4 | Tests use Python stdlib `unittest` only — runnable inside the docker image with no network installs |
| N5 | FOSS only; no vendored third-party code or data |
| N6 | No blocking I/O in the event loop; MQTT subscription callbacks schedule work on the loop |

## 3. System context

```
┌──────────┐  BLE   ┌──────────────────┐  MQTT    ┌─────────────────────┐
│ JK-BMS   │ ◀────▶ │ android bridge   │ ───────▶ │ broker (mosquitto)  │
│ V19 (1.n)│        │ (per-value ret.) │          └─────────┬───────────┘
└──────────┘        └──────────────────┘                    │ subscribe <prefix>/#
                                                    ┌───────▼───────────┐
                                                    │ Home Assistant    │
                                                    │ jkbms_mqtt integ. │
                                                    │ → devices/entities│
                                                    └───────────────────┘
```

## 4. MQTT interface consumed (normative)

Source of truth: android-jkbms-mqtt Spec.md §5.2/5.3 (v1.0.0). Summary
of what this integration subscribes to — base `<prefix>/<name>/`:

| Topic | Payload | Integration use |
|-------|---------|-----------------|
| `availability` | `online`/`offline`, retained | device-wide availability |
| `online` | epoch s of last connect | diagnostic timestamp sensor |
| `voltage` `current` `power` `soc` `soh` | float/int | sensors |
| `capacity_remaining` `capacity_nominal` `cycles` `runtime_s` | float/int | sensors |
| `temperature/mos` `temperature/1` `temperature/2` | °C | sensors (present only when bridge publishes) |
| `cell/<i>/voltage` `cell/<i>/resistance`, i = 1..24 | V / Ω | dynamic per-cell sensors |
| `balancing` `heating` `mos/charge` `mos/discharge` `mos/precharge` | `0`/`1` | binary sensors |
| `balancing_current` `heating_current` | A | sensors |
| `alarm/<alarm>` | `1` retained, empty = cleared | per-alarm binary sensor |
| `alarms` | CSV of active alarm names | aggregate binary sensor + attribute |
| `error_bitmask` | hex `0x…` | diagnostic sensor |
| `device_name` `model` `sw_version` `hw_version` `serial` | strings | device info |

Alarm names (bridge `BmsAlarm`, lowercase slugs):
`cell_undervoltage, cell_overvoltage, pack_undervoltage,
pack_overvoltage, charging_overtemperature, charging_undertemperature,
discharging_overtemperature, discharging_undertemperature,
charging_overcurrent, discharging_overcurrent, short_circuit,
ic_error, locked_mos`.

Unknown subtopics under a device are ignored (forward compatibility).

## 5. Entity catalog

One HA **device** per `<name>`; identifiers `("jkbms_mqtt", <name>)`,
name = `device_name` topic value (fallback `<name>`), model/manufacturer
(`JK BMS`)/sw/hw/serial from the string topics when present.

### 5.1 Sensors

| Entity | Topic | Device class / unit | State class |
|--------|-------|--------------------|-------------|
| Voltage | `voltage` | voltage / V | measurement |
| Current | `current` | current / A | measurement |
| Power | `power` | power / W | measurement |
| State of charge | `soc` | battery / % | measurement |
| State of health | `soh` | battery / % | measurement |
| Capacity remaining | `capacity_remaining` | energy / Ah? no — current-style custom | measurement |
| Capacity nominal | `capacity_nominal` | — / Ah | total |
| Cycles | `cycles` | — / cycles | total_increasing |
| Total runtime | `runtime_s` | duration / s | total_increasing |
| Temperature MOS | `temperature/mos` | temperature / °C | measurement |
| Temperature 1/2 | `temperature/1`, `temperature/2` | temperature / °C | measurement |
| Cell *i* voltage | `cell/<i>/voltage` | voltage / V | measurement |
| Cell *i* resistance | `cell/<i>/resistance` | — / Ω | measurement |
| Balancing current | `balancing_current` | current / A | measurement |
| Heating current | `heating_current` | current / A | measurement |
| Last connect | `online` | timestamp | — (diagnostic) |
| Error bitmask | `error_bitmask` | — | — (diagnostic) |
| Alarms CSV | `alarms` | — | — (diagnostic attribute carrier) |

The bridge's `json` aggregate topic (android spec §5.3) is intentionally
not consumed — per-value topics are the single source of truth.

Capacity topics use unit `Ah` without a standard device class (HA has
no ampere-hour class; battery capacity is expressed via `%` + custom unit).

### 5.2 Binary sensors

| Entity | Topic | On when | Device class |
|--------|-------|---------|--------------|
| Balancing | `balancing` | `1` | battery_charging |
| Heating | `heating` | `1` | heat |
| Charge MOS | `mos/charge` | `1` | plug? none — plain |
| Discharge MOS | `mos/discharge` | `1` | plain |
| Precharge | `mos/precharge` | `1` | plain |
| Alarm *a* (13×) | `alarm/<a>` | `1` | problem |
| Alarms active | `alarms` CSV | non-empty | problem |

MOS states are states, not faults → no `problem` class. Plain binary
sensors for MOS/precharge; `battery_charging` only for balancing,
`heat` for heating (closest semantic match; documented).

### 5.3 Dynamic cells and topics

- Cell entities are created when `cell/<i>/voltage` or
  `cell/<i>/resistance` first arrives; *i* bounded 1..24.
- Temperature sensors 1/2 and MOS temperature exist only when published
  (absent sensors are omitted by the bridge).
- Per-alarm binary sensors exist for the 13 known names; the aggregate
  sensor always exists once any value topic of the device arrived.

## 6. Configuration

- **Config Flow** (`jkbms_mqtt`): single user step asking for the
  topic prefix (string, default `jkbms`, sanitized the same way the
  bridge sanitizes: strip NUL `/` `+` `#`, trim, max 100 per segment).
  Requires the `mqtt` integration to be set up (dependency).
- **Options Flow**: change the prefix live — resubscribe, rebuild
  devices under the new prefix, remove stale entities.
- Multiple config entries are allowed (one per prefix).
- Subscribed topic filter: `<prefix>/#` with QoS 0 (HA MQTT default).

## 7. Availability semantics

1. Every entity of a device inherits availability from
   `<prefix>/<name>/availability` (`online`/`offline`).
2. HA restart: retained value + availability topics restore state.
3. A device stays (stale entities visible as unavailable) when the
   bridge stops publishing; there is no auto-removal of devices.

## 8. Repository layout

```
custom_components/jkbms_mqtt/   the integration (HACS-compatible)
├── __init__.py        entry: forward config entry setup, coordinator
├── manifest.json      domain, dependencies ["mqtt"], version
├── config_flow.py     prefix step + options flow
├── const.py           domain, defaults, alarm list, catalog tables
├── coordinator.py     JkbmsMqttCoordinator: subscribe <prefix>/#, route
├── device.py          per-<name> device + dynamic entity creation
├── sensor.py          SensorEntityDescription-driven catalog
├── binary_sensor.py   binary catalog
└── topology.py        pure topic ↔ (name, field) parsing + sanitizing
tests/                 stdlib unittest, no fixtures
docker/                configuration.yaml + mosquitto.conf for local dev
docker-compose-dev.yaml  clean HA (madebytimo/home-assistant) + mosquitto
AGENTS.md              agent orientation
Spec.md                this file — normative
```

## 9. Testing

- **Unit (dockerized):** `topology.py` topic parsing/sanitizing, catalog
  completeness vs android Spec §5.2, payload→state coercion (floats,
  `0`/`1`, epoch→timestamp, CSV alarms). Runner:
  `docker run --rm -v <repo>:/w -w /w madebytimo/home-assistant
  python3 -m unittest discover -s tests -v` (stdlib only, N4).
- **Manual dev stack:** `docker-compose-dev.yaml` starts a clean HA plus
  a local mosquitto broker; add the `mqtt` and `jkbms_mqtt` entries via
  the UI and verify devices/entities against the bridge's live topics.

## 10. Future work (explicitly out of scope for v1.0)

- Native MQTT discovery emitted by the bridge (would replace this
  listener; android Spec §10)
- Settings write-back / control entities (bridge is read-only)
- Number-of-cells sensor from the enabled-cells bitmask (needs a
  dedicated bridge topic)
- Multiple BMS per config entry filtering / per-device enable flags
