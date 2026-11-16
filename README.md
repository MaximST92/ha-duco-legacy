# Duco (legacy Communication Print) for Home Assistant

Custom integration for Duco ventilation systems controlled by the **older Duco Communication Print** board, the one that answers on `/board_info` and `/nodeinfoget`.

Home Assistant's built-in [Duco integration](https://www.home-assistant.io/integrations/duco/) needs the newer Connectivity Board with public API 2.1+. If it refuses your board with *"Public API needs to be higher than 2.1"*, this integration is for you.

Local polling every 30 s over plain HTTP, no cloud, no extra Python dependencies.

## What you get

One Home Assistant device per Duco node (box, valves, wall controls), named after the room stored in the Duco system and linked to its parent node.

| Entity | On | Notes |
|---|---|---|
| Select **Ventilation state** | box and every valve | `AUTO`, `MAN1`–`MAN3` (timed, uses the node's ManualTimeout), `CNT1`–`CNT3` (permanent) |
| Sensor **CO2**, **Temperature**, **Humidity** | nodes that have that sensor | nodes without one report 0 and are skipped |
| Sensor **Target flow**, **Actual flow** | box and valves | % |
| Sensor **Override remaining** | box and valves | seconds left on a `MANx` override |
| Sensor **Power** | box | W, from `/boxinfoget` |

## Install

**HACS:** HACS → ⋮ → Custom repositories → add this repo's URL as type *Integration* → install **Duco (legacy Communication Print)** → restart.

**Manual:** copy `custom_components/duco_legacy` into your `config/custom_components/` and restart.

Then Settings → Devices & services → Add integration → **Duco (legacy Communication Print)**, and enter the board's IP address.

## Limits

- Nodes are read once at setup. After pairing a new Duco node, reload the integration.
- Humidity-controlled valves without an `rh` value expose only an unlabeled `snsr` number; it's not exposed until its meaning is known.
- The board has no authentication. Keep it on a network segment you trust.

## The legacy API

All plain `GET` over HTTP, JSON responses (sent without a JSON content type):

| Endpoint | Returns |
|---|---|
| `/board_info` | `uptime`, `swversion`, `mac`, `ip` |
| `/nodelist` | `{"nodelist": [1, 2, ...]}` |
| `/nodeinfoget?node=N` | `devtype`, `location`, `state`, `mode`, `trgt`, `actl`, `cntdwn`, `temp`, `co2`, `rh`, `prnt`, `serialnb`, `swversion`, ... |
| `/nodeconfigget?node=N` | settings with `Val`/`Min`/`Inc`/`Max` (AutoMin/Max, Manual1–3, ManualTimeout, CO2Setpoint, ...) |
| `/boxinfoget` | calibration, pressures, `Performance.PowerNow` |
| `/nodesetoperstate?node=N&value=MAN1` | **write**: answers `SUCCESS` or `FAILED` |

[`api-dump/legacy.txt`](api-dump/legacy.txt) is a real (anonymized) dump from a DucoBox with CO₂ and humidity valves. To dump your own board (read-only):

```bash
sh probe.sh <board-ip> > duco-dump.txt
```

## Development

```bash
uv run --python 3.14 --with homeassistant==2026.11.1 python test_entities.py
```

Checks which entities and devices get created from the API dump.
