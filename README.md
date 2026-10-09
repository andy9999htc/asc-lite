# asc-lite

**Unofficial Home Assistant custom integration for deterministic shutter automation (ASC-lite).**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andy9999htc&repository=asc-lite&category=integration)

ASC-lite is a focused Home Assistant integration that implements the required subset of ASC behavior for this installation: astro open/close, per-shutter time windows, per-shutter shading thresholds, party handling, window protection, and manual block behavior.

> **Disclaimer:** This is an unofficial community project. It is not endorsed by or affiliated with Home Assistant, FHEM, or any shutter hardware vendor.

## Changelog

### v0.4.0

- Completed M4 stabilization and pilot acceptance work.
- Added M4 acceptance coverage for scale/inversion, terrace party/window safety, presence-away forced-open, and astro/lux gating.
- Added a rollout package with helper services and pilot evidence tracking in the project docs.
- Updated backlog and README status for release-readiness after the MVP rule and pilot validation phases.

### v0.3.0

- Completed M3 MVP rule set: terrace window protection, party gating, astro open/close, presence handling, and lux shading.
- Added reason-code decision logging for rule-level evidence and local pilot validation.
- Extended standalone validation with M3 dry-run checks and logging output.
- Updated backlog and README project status to reflect M3 completion and the M4 stabilization phase.

### v0.2.5

- Completed M2 command dispatch and manual-block milestone.
- Added deduplicating dispatch logic for cover target commands.
- Added manual override detection and expiry handling for auto-suppression rules.
- Added diagnostic sensor and switch helpers for rule decisions and manual-block state.
- Extended standalone validation with M1/M2 dry-run examples and local regression coverage.

### v0.2.0

- Completed M1 core decision engine milestone.
- Added deterministic rule priority evaluation with stable winning rule selection.
- Added state snapshot layer with unknown/unavailable fallback handling.
- Added unit tests for rule priority and snapshot behavior.
- Extended standalone local validation with M1 engine dry-run checks.

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

Current implementation stage: M4 complete (stabilization, acceptance coverage, and rollout package implemented and validated locally).

Already implemented:

- B-001 Create integration skeleton
- B-002 Add Config Flow and Options Flow
- B-003 Define typed models
- B-004 Build normalization utilities
- B-005 Implement rule priority framework
- B-006 Build state snapshot layer
- B-007 Implement dispatcher with dedupe
- B-008 Implement manual override detection
- B-009 Add diagnostics entities
- B-010 Implement terrace window protection
- B-011 Implement party rule (terrace evening down only)
- B-012 Implement astro open/close rules
- B-013 Implement presence gating and away forced-open set
- B-014 Implement lux shading for non-terrace shutters
- B-015 Implement reason-code decision logging
- B-016 Unit test coverage for engine behavior
- B-017 Pilot acceptance tests and M4 validation
- B-018 Pilot rollout package and evidence tracking

Next planned stage: release validation and pilot deployment / production rollout.

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

## Testing

The project is developed test-first from the beginning:

- Unit tests in tests/ cover model validation and mixed-scale position conversion.
- A standalone script allows local validation without a running Home Assistant instance.

### Unit tests (pytest)

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Run all tests:

```bash
pytest -q
```

### Standalone local test script

Use standalone_asc_lite_test.py to validate config and conversion behavior from environment variables.

Quick start (PowerShell):

```powershell
python .\standalone_asc_lite_test.py
```

With custom environment variables:

```powershell
$env:ASC_NAME="ASC Lite Local"
$env:ASC_SUN_ENTITY_ID="sun.sun"
$env:ASC_PRESENCE_ENTITY_ID="binary_sensor.resident_home"
$env:ASC_AUTO_ENABLED_ENTITY_ID="input_boolean.asc_auto_enabled"
$env:ASC_PARTY_MODE_ENTITY_ID="input_boolean.asc_party_mode"
$env:ASC_INVERT_POSITIONS_GLOBAL="false"
$env:ASC_MANUAL_BLOCK_SECONDS="3600"
$env:ASC_NATIVE_SAMPLE="7"
$env:ASC_COVERS_JSON='[{"cover_entity_id":"cover.rollladen_ez_mitte","name":"EZ Mitte","scale":10,"azimuth_min":110,"azimuth_max":255,"elevation_min":8,"elevation_max":60,"min_temp_c":18,"lux_enter":380,"lux_exit":300,"hysteresis_enabled":true}]'

python .\standalone_asc_lite_test.py
```

Supported environment variables:

- ASC_NAME
- ASC_SUN_ENTITY_ID
- ASC_PRESENCE_ENTITY_ID
- ASC_AUTO_ENABLED_ENTITY_ID
- ASC_PARTY_MODE_ENTITY_ID
- ASC_TERRACE_WINDOW_ENTITY_ID
- ASC_OUTDOOR_TEMP_ENTITY_ID
- ASC_LUX_WZ_ENTITY_ID
- ASC_LUX_EZ_ENTITY_ID
- ASC_INVERT_POSITIONS_GLOBAL
- ASC_MANUAL_BLOCK_SECONDS
- ASC_NATIVE_SAMPLE
- ASC_COVERS_JSON

## Project docs

The MVP spec and implementation details are documented in:

- ASC_LITE_HA_HACS_PFLICHTENHEFT.md
- ASC_LITE_ENTITY_CONTRACT.md
- ASC_LITE_DECISION_TABLE.md
- ASC_LITE_MVP_TESTPLAN.md
- ASC_LITE_IMPLEMENTATION_BACKLOG.md

## Roadmap

Implementation order (summary):

1. M0 Skeleton + Config - completed
2. M1 Core decision engine - completed
3. M2 Dispatch + manual block behavior - completed
4. M3 MVP rule set - completed
5. M4 Stabilization + test completion - completed

Current status: M0-M4 are complete; the project is ready for release validation and pilot rollout.

See ASC_LITE_IMPLEMENTATION_BACKLOG.md for the full task breakdown and evidence trail.

## Known limitations (current phase)

- M4 stabilization and pilot acceptance checks are complete and validated locally.
- The engine is release-ready for pilot deployment, subject to HA runtime validation in the target environment.
- Diagnostics, manual-block, and rollout helper services are implemented and documented.
- README reflects the current architecture and backlog status after M4 completion.

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

MIT
