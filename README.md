# asc-lite

**Unofficial Home Assistant custom integration for deterministic shutter automation (ASC-lite).**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andy9999htc&repository=asc-lite&category=integration)

ASC-lite is a focused Home Assistant integration that implements the required subset of ASC behavior for this installation: astro open/close, per-shutter time windows, per-shutter shading thresholds, party handling, window protection, and manual block behavior.

> **Disclaimer:** This is an unofficial community project. It is not endorsed by or affiliated with Home Assistant, FHEM, or any shutter hardware vendor.

## Changelog

### v0.1.0

- Initial repository bootstrap.
- Added Home Assistant integration skeleton in custom_components/asc_lite.
- Added config flow and options flow foundation.
- Added typed runtime models and validation for global and per-cover settings.
- Added first project documentation set in repository root.

## Features

- Config flow setup directly in Home Assistant UI.
- Options flow for updating global settings and per-cover configuration.
- Typed configuration validation:
  - required entity bindings
  - per-cover scale validation (0..100 or 0..10)
  - per-shutter shading settings validation
- Architecture targets deterministic rule priority and reason-code based decisions.
- No hardcoded Home Assistant entity IDs in integration source.

## Current status

Current implementation stage: M0 (Skeleton + Config + Typed models).

Already implemented:

- B-001 Create integration skeleton
- B-002 Add Config Flow and Options Flow
- B-003 Define typed models

Next planned stage: M1 (core decision engine).

## Requirements

- Home Assistant (current supported Core release)
- HACS installed (recommended installation path)
- Existing shutter cover entities in Home Assistant
- Existing helper/sensor entities for sun, presence, optional lux/temp/window signals

## Installation

### Via HACS (recommended)

1. Open HACS in Home Assistant.
2. Open Menu -> Custom repositories.
3. Add:
   - URL: https://github.com/andy9999htc/asc-lite
   - Category: Integration
4. Search for asc-lite and install.
5. Restart Home Assistant.

### Manual

```bash
cd /path/to/homeassistant/config/custom_components/
git clone https://github.com/andy9999htc/asc-lite.git asc_lite_temp
cp -r asc_lite_temp/custom_components/asc_lite ./
rm -rf asc_lite_temp
```

Restart Home Assistant.

## Configuration

1. Go to Settings -> Devices & Services -> Add Integration.
2. Search for ASC Lite.
3. Enter global settings in the first step:
   - Name
   - Sun entity ID
   - Presence entity ID
   - Auto-enabled helper entity ID
   - Party-mode helper entity ID
   - Optional: terrace window, outdoor temperature, lux WZ, lux EZ entity IDs
   - Global invert flag
   - Manual block duration in seconds
4. Paste per-cover JSON in the second step.

### Per-cover JSON format

Each cover object supports:

- cover_entity_id
- name
- scale (10 or 100)
- azimuth_min
- azimuth_max
- elevation_min
- elevation_max
- min_temp_c
- lux_enter
- lux_exit
- hysteresis_enabled

Example:

```json
[
  {
    "cover_entity_id": "cover.rollladen_wohnzimmer",
    "name": "Wohnzimmer",
    "scale": 100,
    "azimuth_min": 120,
    "azimuth_max": 260,
    "elevation_min": 10,
    "elevation_max": 65,
    "min_temp_c": 18,
    "lux_enter": 400,
    "lux_exit": 300,
    "hysteresis_enabled": true
  },
  {
    "cover_entity_id": "cover.rollladen_ez_mitte",
    "name": "EZ Mitte",
    "scale": 10,
    "azimuth_min": 110,
    "azimuth_max": 255,
    "elevation_min": 8,
    "elevation_max": 60,
    "min_temp_c": 18,
    "lux_enter": 380,
    "lux_exit": 300,
    "hysteresis_enabled": true
  }
]
```

## Project docs

The MVP spec and implementation details are documented in:

- ASC_LITE_HA_HACS_PFLICHTENHEFT.md
- ASC_LITE_ENTITY_CONTRACT.md
- ASC_LITE_DECISION_TABLE.md
- ASC_LITE_MVP_TESTPLAN.md
- ASC_LITE_IMPLEMENTATION_BACKLOG.md

## Roadmap

Implementation order (summary):

1. M0 Skeleton + Config
2. M1 Core decision engine
3. M2 Dispatch + manual block behavior
4. M3 MVP rule set
5. M4 Stabilization + test completion

See ASC_LITE_IMPLEMENTATION_BACKLOG.md for the full task breakdown.

## Known limitations (current phase)

- Rule engine behavior is not fully active until M1-M3 tasks are completed.
- Diagnostics entities and service helpers are planned for later milestones.
- README reflects active architecture decisions, but feature completeness follows the backlog milestones.

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

MIT
