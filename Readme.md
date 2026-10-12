# JK BMS MQTT integration for Home Assistant

Home Assistant custom integration that maps the per-value MQTT topics
published by the `android-jkbms-mqtt` bridge to
Home Assistant devices, sensors and binary sensors.

## Installation

**Manual:** copy `custom_components/jkbms_mqtt/` into the `custom_components/`
directory of your HA configuration and restart Home Assistant.

**HACS:** add this repository as a *custom repository* (type
*integration*), then install `JK BMS MQTT` from it.

## Development

Unit tests:

```sh
docker run --rm -v "$PWD:/w" -w /w --entrypoint /bin/sh \
    madebytimo/home-assistant:latest \
    -c 'python3 -m unittest discover -s tests -v'
```

Local dev stack (clean Home Assistant + mosquitto for manual testing):

```sh
docker compose --file docker-compose-dev.yaml up
```
