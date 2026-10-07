# ASC-lite MVP Entity Contract

Status: Draft v1
Source baseline: `fhem/docs/rollladen_asc_inventory.md`

## 1) Purpose

This contract defines all Home Assistant entities required for ASC-lite MVP, including types, expected states, and fallback behavior when entities are unavailable.

## 2) Global Rules

| Entity IDs | No hardcoded HA entity IDs in source code. All entity bindings are configured through integration options/config flow. |
| Position semantics | All shutters use the same direction: `0=open`, `10/100=closed`. |
| Position scale | 6 shutters use 0..100; 3 Esszimmer shutters use 0..10. Normalize internally to 0..100 for decision logic and denormalize per device on command dispatch. |
| Manual block scope | Manual block suppresses shading/comfort auto actions only; it does not suppress evening-down actions for any shutter or safety/window protection actions. |
| Global auto policy | If `auto_enabled` is off, all auto actions (astro, presence, lux, etc.) are suppressed; manual actions remain possible. |
| Topic | Rule |
| --- | --- |
| Config key | Type | Allowed values | Required | Fallback if missing |
| Timezone | Use HA local timezone for all time-window comparisons. |
| `sun_entity_id` | sun | HA sun states/attributes | yes | Disable astro moves and log `astro_source_missing`. |
| `presence_entity_id` | binary_sensor or sensor | configurable | yes | Treat as `home` and log `presence_missing`. |
| `presence_home_values` | list[str] | configurable | yes | Defaults: `home`, `on`, `present`. |
| `presence_away_values` | list[str] | configurable | yes | Defaults: `away`, `off`, `absent`. |
| `outdoor_temp_entity_id` | sensor | float (degC) | should | Disable temperature gate for shading. |
| `lux_wz_entity_id` | sensor | float lux | should | Disable lux-driven shading for WZ group. |
| `lux_ez_entity_id` | sensor | float lux | should | Disable lux-driven shading for EZ group. |
| `terrace_window_entity_id` | binary_sensor | `on`/`off` | yes for terrace behavior | Disable ventilate-inhibit rule for terrace and log warning. |
| `auto_enabled_entity_id` | input_boolean | `on`/`off` | yes | Default `on`. |
| `party_mode_entity_id` | input_boolean | `on`/`off` | yes | Default `off`. |
| `sun.sun` | sun | HA sun states/attributes | yes | Disable astro moves and log `astro_source_missing`. |
| `binary_sensor.resident_home` | binary_sensor | `on`/`off` | yes | Treat as `home` and log `presence_missing`. |
| Cover | Config key (`cover_entity_id`) | Native scale | Open pos | Closed pos | Ventilate pos | Shading pos | Time up early | Time up late | Time down early | Time down late |
| `sensor.lux_wz` | sensor | float lux | should | Disable lux-driven shading for WZ group. |
| Rollladen_Wohnzimmer | configured | 0..100 | 0 | 80 | 70 | 35 | 06:15 | 09:00 | 16:30 | 22:00 |
| Rollladen_Terrasse | configured | 0..100 | 0 | 80 | 55 | 35 (not used in MVP shading) | 06:15 | 09:00 | 16:30 | 22:15 |
| Rollladen_Amelie_Fenster | configured | 0..100 | 0 | 99 | 60 | 60 | 07:45 | 09:30 | 16:30 | 22:00 |
| Rollladen_Amelie_Tuer | configured | 0..100 | 0 | 99 | 55 | 55 | 07:45 | 09:30 | 16:30 | 22:00 |
| Rollladen_Schlafzimmer_Fenster | configured | 0..100 | 0 | 99 | 60 | 60 | 08:30 | 09:30 | 16:30 | 22:00 |
| Rollladen_Schlafzimmer_Tuer | configured | 0..100 | 0 | 99 | 35 | 55 | 08:30 | 09:30 | 16:30 | 22:00 |
| Rollladen_EZ_links | configured | 0..10 | 0 | 10 | 7 | 6 | 05:58 | 09:30 | 16:30 | 22:00 |
| Rollladen_EZ_mitte | configured | 0..10 | 0 | 9 | 7 | 6 | 05:58 | 09:30 | 16:30 | 22:00 |
| Rollladen_EZ_rechts | configured | 0..10 | 0 | 9 | 7 | 7 | 05:58 | 09:30 | 16:30 | 22:00 |
| Rollladen_Wohnzimmer | `cover.rollladen_wohnzimmer` | 0 | 80 | 70 | 35 | 06:15 | 09:00 | 16:30 | 22:00 |
| Rollladen_Terrasse | `cover.rollladen_terrasse` | 0 | 80 | 55 | 35 | 06:15 | 09:00 | 16:30 | 22:15 |
Notes:
- All cover IDs are provided by config flow/options and can be changed without code changes.
- Inversion is global only: `invert_positions_global` (bool) applies to all shutters equally.
- No per-cover inversion switch in MVP.
| Rollladen_Schlafzimmer_Fenster | `cover.rollladen_schlafzimmer_fenster` | 0 | 99 | 60 | 60 | 08:30 | 09:30 | 16:30 | 22:00 |
| Rollladen_Schlafzimmer_Tuer | `cover.rollladen_schlafzimmer_tuer` | 0 | 99 | 35 | 55 | 08:30 | 09:30 | 16:30 | 22:00 |
| Group | Members | Lux sensor | Presence gating |
| Rollladen_EZ_mitte | `cover.rollladen_ez_mitte` | 0 | 9 | 7 | 6 | 05:58 | 09:30 | 16:30 | 22:00 |
| Rollladen_EZ_rechts | `cover.rollladen_ez_rechts` | 0 | 9 | 7 | 7 | 05:58 | 09:30 | 16:30 | 22:00 |

Notes:

MVP constraints:
- Terrace has no shading in MVP (morning up, evening down, window ventilate protection).
- Party mode affects terrace evening down only.
- Entity IDs above are target names and must be validated against real HA IDs.
- If a cover uses inverted semantics in HA integration, set `invert_position=true` in integration options.
| Provide all 9 target cover entity IDs in integration options | user | open |
## 5) Per-Shutter Runtime Helpers

| Entity pattern | Type | Required | Description |
| Confirm single global inversion flag (`invert_positions_global`) | user | open |
| `input_boolean.asc_lite_manual_block_<name>` | input_boolean | yes | Manual lock flag for one shutter. The manual block is scoped to shading/comfort auto logic; evening-down actions remain allowed for all shutters. |
| `timer.asc_lite_manual_block_<name>` | timer | yes | Auto-expire manual lock. |
| `input_boolean.asc_lite_cmd_internal_<name>` | input_boolean | yes | Internal command marker to separate auto/manual drives. |

## 6) Per-Shutter Mapping (kein Gruppenmodell)

Im MVP werden keine Gruppen-Policies verwendet. Jeder Shutter bekommt seine Konfiguration separat, inklusive eigener Shading- und Zeitfenster-Werte.

| Shutter | Cover entity | Lux sensor | Min temp | Azimuth/Elevation | Presence gating |
| --- | --- | --- | --- | --- | --- |
| configurable per shutter | configured in options | configured in options | configured in options | configured in options | configured in options |

Notes:
- Gruppierung ist kein Muss und soll im MVP nicht eingesetzt werden.
- Die Logik bleibt per Shutter deterministisch und nachvollziehbar.

## 7) Error and Fallback Contract

| Condition | Behavior | Reason code |
| --- | --- | --- |
| Cover unavailable | Skip command, retain queue-free design, log warning | `cover_unavailable` |
| Sun source unavailable | Disable astro actions, keep manual/party/window logic active | `astro_source_missing` |
| Lux sensor stale > 15m | Skip lux transition, keep last stable mode | `lux_stale` |
| Presence unavailable | Treat as `home` (no forced security close) | `presence_missing` |
| Window sensor unavailable | Do not enforce terrace ventilate guard | `window_sensor_missing` |

## 8) Open Validation Items (fill before coding)

| Item | Owner | Status |
| --- | --- | --- |
| Provide all 9 target cover entity IDs via config flow/options, not via hardcoded source values | user | open |
| Confirm presence entity final ID at runtime configuration | user | open |
| Confirm lux sensor entity IDs and update rate at runtime configuration | user | open |
| Confirm outdoor temp entity ID at runtime configuration | user | open |
| Confirm invert flag per cover in config | user | open |
| Confirm `closed=9` for EZ_mitte and EZ_rechts | user | resolved |
| Manual block applies only to shading/comfort auto actions, not to evening-down actions for any shutter | user | resolved |
| Set default manual block duration to 3600s (1h) | user | resolved |

Notes:
- No HA entity IDs are required in the Python code itself.
- Configuration is the source-of-truth for all bindings; the code must work with arbitrary valid HA IDs.
- `closed=9` for EZ_mitte and EZ_rechts is the valid default in the MVP.
- Manual block default is 1 hour and should not suppress the sunset evening drive for any shutter.

