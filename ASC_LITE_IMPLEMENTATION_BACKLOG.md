# ASC-lite MVP Implementation Backlog

Status: Draft v1
Source docs:
- fhem/docs/ASC_LITE_HA_HACS_PFLICHTENHEFT.md
- fhem/docs/ASC_LITE_ENTITY_CONTRACT.md
- fhem/docs/ASC_LITE_DECISION_TABLE.md
- fhem/docs/ASC_LITE_MVP_TESTPLAN.md

## 1) Ziel

Diese Liste beschreibt die konkrete Implementierungsreihenfolge fuer custom_components/asc_lite inkl. Akzeptanzkriterien pro Task.

## 2) Meilensteine

1. [x] M0 - Skeleton + Config
2. [x] M1 - Core Decision Engine (ohne Cover-Kommandos)
3. [x] M2 - Command Dispatch + Manual Block
4. [ ] M3 - MVP Rules live (Terrasse, Party, Presence-away Sonderregel)
5. [ ] M4 - Stabilisierung + Testabschluss

## 2a) Test-Policy (verbindlich)

1. Jede Implementierungsaufgabe wird von Anfang an mit Tests umgesetzt (test-first oder test-parallel im selben Task).
2. Pro Ticket gilt: kein "done" ohne mindestens einen passenden Testfall (Unit oder Integration) und lokalen Lauf.
3. `standalone_asc_lite_test.py` wird pro Phase mit gepflegt, damit Kernlogik ohne HA lokal pruefbar bleibt.
4. Vor Merge in `main`: `pytest -q` muss gruen sein.

## 2b) Testaktivitaeten pro Phase

### M0 - Skeleton + Config
- Config-/Model-Validierungstests (`tests/test_models.py`) fuer Pflichtfelder, Skalen, Inversion, Hysterese.
- Standalone-Skript validiert Env-basierte Konfiguration ohne HA.

### M1 - Core Decision Engine
- Unit-Tests fuer Position/Normalisierung und Prioritaetsentscheidungen (`tests/test_position.py`, spaeter `tests/test_priority.py`).
- Standalone-Skript erweitert um Engine-Samples (Decision Dry-Run ohne Dispatch).

### M2 - Dispatch + Manual Block
- Unit-Tests fuer Dedupe, Marker-Handling und Manual-Block-Semantik.
- Restart-/Persistenztests fuer Block-Expiry (Storage Restore).
- Standalone-Skript erweitert um Dispatch-Simulation (ohne echten HA Service Call).

### M3 - MVP Rules
- Regeltests gegen Decision-Table IDs (R-WIN, R-PARTY, R-ASTRO, R-PRES, R-LUX).
- Integrationsnahe Flow-Tests fuer Pilot-Shutter inkl. Zeitfenster und Inversion.
- Standalone-Skript erweitert um regelbezogene Szenarien per Env-Profil.

### M4 - Stabilisierung + Abschluss
- Vollstaendiger Lauf aller Unit- und Integrations-Tests.
- Mapping der Tests auf `ASC_LITE_MVP_TESTPLAN.md` (T-001..T-022) inkl. Evidenz.
- 7-Tage Pilotnachweis dokumentiert.

## 3) Backlog (priorisiert)

## M0 - Skeleton + Config

### B-001 Create integration skeleton
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/manifest.json
  - custom_components/asc_lite/__init__.py
  - custom_components/asc_lite/const.py
- Scope:
  - Domain, version, dependencies, logger namespace
  - Setup/Unload entry scaffolding
- DoD:
  - Integration can be loaded/unloaded without entities
  - No startup errors in HA logs

### B-002 Add Config Flow and Options Flow
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/config_flow.py
  - custom_components/asc_lite/translations/en.json
- Scope:
  - All entity IDs configurable, no hardcoded IDs
  - Global inversion flag (invert_positions_global)
  - Per-cover scale (0..100 or 0..10)
- DoD:
  - Entry creation works from UI
  - Option changes persist and reload entry

### B-003 Define typed models
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/models.py
- Scope:
  - Dataclasses/pydantic-like structs for:
    - GlobalConfig
    - CoverConfig
    - ShadingConfig
    - ThresholdConfig
  - Per-shutter config values:
    - `azimuth_min`, `azimuth_max`
    - `elevation_min`, `elevation_max`
    - `min_temp_c`
    - `lux_enter`, `lux_exit`
    - `hysteresis_enabled`
- DoD:
  - Validation rejects missing required bindings
  - Scale/inversion constraints validated
  - Shading config is per shutter, no group model required

## M1 - Core Decision Engine

### B-004 Build normalization utilities
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/position.py
- Scope:
  - normalize native -> 0..100
  - denormalize 0..100 -> native scale
  - global inversion transform applied consistently
- DoD:
  - Unit tests for 0..100 and 0..10 covers pass
  - Inversion test passes for all conversions

### B-005 Implement rule priority framework
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/priority.py
  - custom_components/asc_lite/engine/types.py
- Scope:
  - Rule registration and deterministic priority execution
  - First winning action per evaluation cycle
- DoD:
  - Same input state always yields same winning rule
  - Structured decision object includes rule_id + reason_code

### B-006 Build state snapshot layer
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/coordinator.py
  - custom_components/asc_lite/engine/state.py
- Scope:
  - Collect current states for all configured entities
  - Guard unknown/unavailable behavior
- DoD:
  - Snapshot contains all required fields
  - Missing/stale entities mapped to fallback states

## M2 - Command Dispatch + Manual Block

### B-007 Implement dispatcher with dedupe
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/dispatch.py
- Scope:
  - Single command path to cover.set_cover_position
  - 30s dedupe per cover + target position
- DoD:
  - Duplicate target commands suppressed
  - Dispatch returns executed/suppressed with reason

### B-008 Implement manual override detection
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/manual.py
  - custom_components/asc_lite/storage.py
- Scope:
  - Internal command marker per shutter
  - External/manual move detection
  - Block timer per shutter with restore support
  - Manual block suppresses only shading/comfort auto actions; evening-down actions for any shutter and safety/window rules remain allowed
- DoD:
  - Manual move sets block state
  - Auto shading/comfort actions are suppressed during block
  - Evening-down actions for any shutter and safety/window-triggered movements are not suppressed by the manual block
  - Restart restores block expiry correctly

### B-009 Add diagnostics entities
- Status: [x] umgesetzt
- Priority: P1
- Files:
  - custom_components/asc_lite/sensor.py
  - custom_components/asc_lite/switch.py
- Scope:
  - last_decision_rule
  - last_decision_reason
  - manual_block_active per shutter
  - optional auto_enabled and party switches (bound IDs)
- DoD:
  - Diagnostic sensors update on each evaluation
  - Values are human-readable and stable

## M3 - MVP Rules

### B-010 Implement terrace window protection
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/window.py
  - custom_components/asc_lite/engine/rules.py
- Scope:
  - If terrace window open: terrace -> ventilate position
  - Resume normal processing when closed
- DoD:
  - Rule IDs align with decision table (R-WIN-001/002)

### B-011 Implement party rule (terrace evening down only)
- Status: [x] umgesetzt
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/party.py
  - custom_components/asc_lite/engine/rules.py
- Scope:
  - Party mode suppresses only terrace evening close
  - Does not affect other shutters
- DoD:
  - R-PARTY-001/002 behavior verified

### B-012 Implement astro rules
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/astro.py
  - custom_components/asc_lite/engine/time_window.py
- Scope:
  - Morning: CIVIL open
  - Evening: sun elevation crosses -6 close
  - Respect per-cover time windows
- DoD:
  - R-ASTRO-001/002 pass
  - Outside-window actions suppressed with reason

### B-013 Implement presence rules (including away forced open set)
- Priority: P0
- Files:
  - custom_components/asc_lite/engine/presence.py
  - custom_components/asc_lite/engine/rules.py
- Scope:
  - Normal presence gate handling
  - Away forced-open for:
    - Rollladen_Amelie_Fenster
    - Rollladen_Amelie_Tuer
    - Rollladen_Schlafzimmer_Fenster
    - Rollladen_Schlafzimmer_Tuer
- DoD:
  - R-PRES-001/002/003 behavior verified

### B-014 Implement lux shading (non-terrace only)
- Priority: P1
- Files:
  - custom_components/asc_lite/engine/shading.py
  - custom_components/asc_lite/engine/rules.py
- Scope:
  - Per-shutter shading thresholds and hysteresis
  - Azimuth/elevation gating and minimum-temperature gate per shutter
  - Terrace excluded from shading logic
- DoD:
  - R-LUX-001/002 behavior verified
  - Shading condition is evaluated per shutter using configured azimuth/elevation/min-temp/lux thresholds
  - No group-based shading model is used in MVP

### B-015 Implement reason-code logging
- Priority: P1
- Files:
  - custom_components/asc_lite/logging.py
  - custom_components/asc_lite/coordinator.py
- Scope:
  - Log every decision: shutter, trigger, rule_id, result, reason_code
- DoD:
  - Logs are sufficient for T-001..T-022 evidence

## M4 - Stabilisierung + Testabschluss

### B-016 Unit tests for engine
- Priority: P0
- Files:
  - tests/test_position.py
  - tests/test_priority.py
  - tests/test_time_window.py
  - tests/test_presence.py
  - tests/test_party.py
  - tests/test_window.py
- DoD:
  - Core rule tests green in CI/local

### B-017 Integration tests for pilot shutters
- Priority: P0
- Files:
  - tests/test_mvp_flows.py
- Scope:
  - Map to T-001..T-015
  - Include T-021/T-022 scale + inversion
- DoD:
  - All MVP acceptance tests pass

### B-018 Pilot rollout package
- Priority: P1
- Files:
  - custom_components/asc_lite/services.yaml
  - fhem/docs/ASC_LITE_MVP_TESTPLAN.md
- Scope:
  - Add helper services for controlled manual testing
  - Fill test evidence table during pilot
- DoD:
  - 7-day pilot evidence recorded

## 4) Definition of Done (overall MVP)

1. No hardcoded entity IDs anywhere in integration code.
2. If `auto_enabled` is off, all auto actions are suppressed and only manual actions remain possible.
3. Party rule affects only terrace evening down.
4. Manual block suppresses shading/comfort auto actions only; it does not suppress evening-down actions for any shutter or safety/window-triggered actions.
5. Presence-away forced-open set works for the 4 configured shutters.
6. Scale handling works for both native scales (0..100 and 0..10).
7. Global inversion flag works consistently for all shutters.
8. Shading logic is configured per shutter and uses azimuth/elevation/min-temp/lux hysteresis settings.
9. Tests from ASC_LITE_MVP_TESTPLAN.md completed for pilot scope.

## 5) Implementation Order (quick start)

1. B-001
2. B-002
3. B-003
4. B-004
5. B-005
6. B-006
7. B-007
8. B-008
9. B-010
10. B-011
11. B-012
12. B-013
13. B-014
14. B-015
15. B-016
16. B-017
17. B-018

Test-Gates pro Reihenfolgeblock:
- Nach B-003: Config/Model Tests + Standalone Check muessen gruen sein.
- Nach B-006: Engine-Basis-Tests (Position/Priority/State) muessen gruen sein.
- Nach B-008: Dispatch/Manual Tests muessen gruen sein.
- Nach B-015: Regeltests + Diagnose-Checks muessen gruen sein.
- Nach B-018: Volltest inkl. Pilot-Evidenz abgeschlossen.

## 6) Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Race conditions between triggers | wrong moves | Single coordinator evaluation loop + dedupe |
| Incorrect scale conversion | wrong target positions | Mandatory position normalization tests |
| Presence semantics mismatch | unexpected opens/closes | Configurable home/away value sets |
| Restart during manual block | lost suppression | Persist block expiry in storage |

## 7) Konfigurationsdaten, nicht hardcodierte IDs

1. Die HA-Entity-IDs für alle 9 Covers, Presence-, Lux-, Sun- und Fenster-Sensoren werden über Config Flow / Options übergeben. Sie dürfen nicht hardcodiert im Code stehen.
2. Die Integration muss bei der Konfiguration validieren, ob die übergebenen Entity-IDs existieren; fehlende Werte werden als Konfigurationsfehler oder Warnung behandelt, aber nicht als Code-Abhängigkeit.
3. Beispielwerte aus der Testumgebung dürfen nur als Referenz dienen; sie werden nicht in den Code als feste IDs eingetragen.
4. Für EZ_mitte und EZ_rechts ist `closed=9` korrekt; diese Annahme ist bestätigt und kann als Vorgabe übernommen werden.
5. Standarddauer für Manual-Block, falls nicht in der Konfiguration angegeben: 3600s (1h). Sie soll nur tagsüber die Steuerung überschreiben und die Abendrunterfahrt bei Sonnenuntergang nicht behindern.
6. Azimuth, Elevation, Min-Temp sowie Lux-Hysterese werden pro Shutter konfiguriert; es gibt im MVP kein Gruppenmodell.
