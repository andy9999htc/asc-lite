# asc-lite

**Unofficial Home Assistant custom integration for deterministic shutter automation (ASC-lite).**

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Open your Home Assistant instance and open a repository inside HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andy9999htc&repository=asc-lite&category=integration)

ASC-lite is a focused Home Assistant integration that implements the required subset of ASC behavior for this installation: astro open/close, per-shutter time windows, per-shutter shading thresholds, party handling, window protection, and manual block behavior.

> **Disclaimer:** This is an unofficial community project. It is not endorsed by or affiliated with Home Assistant, FHEM, or any shutter hardware vendor.

## Changelog

### v0.6.9

- Changed astro open/close to time-window matching based on `sun.next_rising` and `sun.next_setting` so `R-ASTRO-001` and `R-ASTRO-002` no longer depend on sun elevation.
- Added regression coverage for time-based astro matching in morning and evening windows.

### v0.6.8

- Added evening-close time window guard: `R-ASTRO-001` is now allowed only until `sun.next_setting + 10 minutes` and skipped afterwards.
- Extended sun snapshot payload with `next_setting` to support deterministic evening window evaluation.
- Added regression coverage for evening close behavior before and after the sunset grace-window cutoff.

### v0.6.7

- Replaced fixed morning-open cutoff with dynamic sunrise-window logic: `R-ASTRO-002` is now allowed only until `sun.next_rising + 10 minutes`.
- Added robust sunrise anchoring for daytime evaluations when Home Assistant already reports the next day's `next_rising`.
- Kept close-target proximity guard for morning-open so custom `close_position` values remain stable with Lux shading.
- Added regression coverage for sunrise grace-window behavior before/after cutoff.

### v0.6.6

- Fixed daytime astro morning-open behavior so it no longer suppresses Lux shading after the cover is already open.
- Added regression coverage to ensure astro only drives the morning transition from a closed state.
- Kept evening astro close unchanged.

### v0.6.5

- Added per-cover position settings in config JSON: `close_position`, `shading_position`, and `ventilate_position`.
- Kept `open_position` fixed at 100 by design.
- Wired runtime evaluation to use per-cover target positions for astro close, lux shading in, and terrace window ventilation.
- Added explicit unit tests for per-cover position defaults, per-cover overrides, and 0..100 range validation.

### v0.6.0

- Refactored presence logic to use blocker pattern: presence now blocks astro morning open for kids when presence=home instead of acting as standalone away/home actions.
- Removed R-PRES-001 (Presence Away Close) and R-PRES-003 (Presence Home Open) rules from priority matrix.
- Kept R-PRES-002 (Presence Away Forced Open) for kids-only shutters to maintain away state protection.
- Extended astro morning open evaluation with presence blocker: kids' shutters are prevented from opening when presence=home.
- Added comprehensive INFO/DEBUG logging throughout coordinator lifecycle and periodic evaluation loop.
- Created deploy-to-ha.ps1 PowerShell script for faster local development workflow with SSH-based file sync to Raspberry Pi.
- Updated decision table and engine to reflect new presence role as gate/blocker rather than independent action generator.
- All runtime behavior validated in production Home Assistant environment.

### v0.5.5

- Added availability guard in runtime dispatch path so unavailable/missing covers are skipped before calling `cover.set_cover_position`.
- Added regression coverage to ensure unavailable covers are marked as suppressed with reason `COVER_UNAVAILABLE` and do not receive dispatch calls.

### v0.5.0

- Added Home Assistant runtime coordinator wiring with periodic evaluation and live dispatch path.
- Added real diagnostic sensor/switch entities and runtime service handlers (`set_manual_block`, `clear_manual_block`, `set_party_mode`, `set_auto_enabled`).
- Added runtime smoke and service tests for entity visibility, service registration, and first live evaluation behavior.

### v0.4.1

- Fixed public metadata consistency for HACS by pointing manifest documentation and issue tracker URLs to the real repository.
- Added a follow-up maintenance release so HACS installations pick up the corrected metadata from a fresh tag.

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

Current implementation stage: M5 complete (runtime wiring, visibility, and service control implemented and validated locally).

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
- B-019 Runtime coordinator wiring in Home Assistant lifecycle
- B-020 Real diagnostic sensor/switch entities in Home Assistant
- B-021 Runtime service registration and handlers
- B-022 Runtime smoke tests and documentation alignment

Next planned stage: pilot hardening and in-environment acceptance evidence.

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
- close_position (0..100, default 0)
- shading_position (0..100, default 35)
- ventilate_position (0..100, default 35)
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
    "close_position": 0,
    "shading_position": 35,
    "ventilate_position": 35,
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
    "close_position": 0,
    "shading_position": 40,
    "ventilate_position": 35,
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
- Runtime smoke tests cover service registration, entity creation, and first live evaluation behavior.
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
6. M5 HA runtime wiring + visibility - completed

Current status: M0-M5 are complete; the project is ready for pilot hardening and runtime evidence capture.

See ASC_LITE_IMPLEMENTATION_BACKLOG.md for the full task breakdown and evidence trail.

## Known limitations (current phase)

- Runtime wiring is implemented and covered by local smoke tests, but final evidence still depends on long-running HA pilot observations.
- Manual-block persistence across Home Assistant restarts is currently memory-scoped in runtime and should be validated/extended during pilot hardening.
- Weather/safety expansions and advanced external triggers remain outside MVP scope.
- README reflects the current architecture and backlog status after M5 completion.

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

MIT
