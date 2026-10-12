# AGENTS.md

Orientation for AI coding agents working in this repository.

## Project overview

Home Assistant custom integration (domain `jkbms_mqtt`) that maps the
per-value MQTT topics published by the `android-jkbms-mqtt` bridge (JK-BMS V19
BLE→MQTT bridge) to HA devices, sensors and binary sensors. Pure
Python, no runtime requirements beyond HA core + its `mqtt` integration.
`Spec.md` at the repo root is **normative** — read it before changing
topic handling, entity catalog or config flow behavior. The consumed
interface is normative in the bridge's `Spec.md` §5.

## Repository layout

```
custom_components/jkbms_mqtt/   the integration (HACS-compatible)
├── const.py          catalog tables + constants; import-clean (no ha imports)
├── topology.py       pure topic parsing + prefix sanitizing; stdlib only
├── payloads.py       payload coercion, unique-id slugs; stdlib only
├── device.py         per-<name> device state (pure dataclass)
├── coordinator.py    mqtt subscription, routing, listener fan-out
├── config_flow.py    prefix config + options flow
├── sensor.py         JkbmsEntity base + sensor platform (incl dynamic cells)
└── binary_sensor.py  binary platform (flags, alarms aggregate + per-alarm)
tests/                stdlib unittest, no fixtures
docker/               configuration.yaml + mosquitto.conf for local dev
docker-compose-dev.yaml  clean dev stack: ha + mosquitto
Spec.md               normative spec (do not edit casually)
```

## Build & test

Host has no pip/venv — everything runs in the docker image (HA 2026.8,
Python 3.14):

```sh
# unit tests (stdlib unittest, no network)
docker run --rm -v "$PWD:/w" -w /w --entrypoint /bin/sh \
    madebytimo/home-assistant:latest \
    -c 'python3 -m unittest discover -s tests -v'

# clean local ha + broker for manual testing (fresh state each run)
docker compose --file docker-compose-dev.yaml down --volumes
rm -rf data-local
docker compose --file docker-compose-dev.yaml up --detach
```

## HA image quirks

- Entrypoint symlinks `configuration/custom_components` →
  `/opt/home-assistant/custom_components`; the compose file mounts the
  repo `custom_components/` over that path (read-only).
- `hass` runs with `--skip-pip`: `manifest.json` `requirements` must
  stay `[]` — a non-empty list aborts startup.
- HA data lives in `/media/home-assistant`; compose bind-mounts
  `./data-local` there. `data-local/` is gitignored.
- `default_config` fails in this image (go2rtc binary missing) —
  `docker/configuration.yaml` lists minimal components instead.
- MQTT message callbacks must be decorated `@callback`
  (`coordinator._route`): without it HA runs them as executor jobs and
  `async_add_entities` from that context destroys pending tasks
  ("Task was destroyed but it is pending"). Coordinator keeps the
  module import-clean for tests via a try/except fallback for
  `homeassistant.core.callback`.

## Critical conventions

- **Comments**: short, lowercase, single line, only for non-obvious
  code. No prose repeating what code says.
- **Spec.md is orchestrator-owned**: agents do not edit it; propose
  changes instead.
- Prefix sanitization must stay byte-compatible with the bridge's
  `TopicMapping.sanitizePrefix` (strip NUL `/` `+` `#` per segment,
  trim, cap 100, empty→default `jkbms`).
- Entity unique ids derive from `<name>` + topic path via
  `payloads.unique_id_for` — never from list positions; they must stay
  stable across restarts and prefix changes.
- `const.py`, `topology.py`, `payloads.py`, `device.py` stay
  import-clean (no homeassistant imports) — unit tests import them
  without HA. HA imports live in the platform/coordinator modules
  (coordinator defers its mqtt import into `listen()`).
- Unknown subtopics stay routed as values (forward compat per spec).
- No new runtime dependencies. Tests use stdlib `unittest` only.
- Python target is the interpreter inside the docker image (3.14).
