# ASC-lite MVP Test Plan

Status: Draft v1

## 1) Test Scope

Pilot shutters for MVP acceptance:

1. `cover.rollladen_wohnzimmer`
2. `cover.rollladen_terrasse`
3. `cover.rollladen_ez_links`

Secondary verification shutters (after pilot):

- `cover.rollladen_ez_mitte`
- `cover.rollladen_ez_rechts`
- `cover.rollladen_amelie_fenster`
- `cover.rollladen_amelie_tuer`
- `cover.rollladen_schlafzimmer_fenster`
- `cover.rollladen_schlafzimmer_tuer`

## 2) Environment Preconditions

| Check | Expected |
| --- | --- |
| All 9 configured cover entities available | yes |
| Presence entity from integration options available | yes |
| Lux sensor entities from integration options available | yes |
| Terrace window entity from integration options available | yes |
| Outdoor temperature sensor available | preferred |
| ASC-lite auto enabled | on |
| `auto_enabled`=off disables all auto actions | yes |
| Party mode | off |
| Party mode affects terrace evening down only | yes |
| Manual block affects shading/comfort auto actions only; not evening-down actions for any shutter | yes |
| Global inversion flag validated once for all shutters | yes |
| Scale mapping validated (6x 0..100, 3x 0..10) | yes |

## 3) Core Functional Tests

| ID | Scenario | Steps | Expected |
| --- | --- | --- | --- |
| T-001 | Morning astro open | Simulate/await civil dawn in up window | Shutter opens to configured open pos; reason `astro_morning_open` |
| T-002 | Evening astro close | Simulate sun elevation crossing -6 in down window | Shutter closes to configured closed pos; reason `astro_evening_close` |
| T-003 | Up window guard | Trigger open outside up window | Command suppressed; reason `outside_time_window` |
| T-004 | Down window guard | Trigger close outside down window | Command suppressed; reason `outside_time_window` |
| T-005 | Party suppression scope | Enable party mode then trigger terrace evening close and other shutter close | Terrace evening close suppressed, other shutters unchanged by party rule |
| T-006 | Party resume | Disable party mode | Terrace evening close rule resumes |
| T-007 | Manual override detect | Move cover manually | Manual block starts; reason `manual_override_detected` |
| T-008 | Manual block enforce | Trigger auto shading/comfort action while manual block active | No movement for shading/comfort action; reason `manual_block_active` |
| T-008A | Manual block does not suppress evening down | Trigger evening-down action for any shutter while manual block active | Shutter still executes evening down if time window and safety rules allow; reason remains `astro_evening_close` or equivalent rule |
| T-009 | Manual block expiry | Wait timer expiry then trigger auto | Auto action executes again |
| T-010 | Terrace window protection | Set terrace window sensor to open near evening close | Terrace moves/stays at ventilate pos; reason `terrace_window_open_ventilate` |
| T-011 | Terrace resume | Close terrace window sensor | Normal rule processing resumes |
| T-012 | Lux shading in | Raise lux above entry threshold with valid azimuth/elevation | Move to shading pos on non-terrace shutters only; reason `lux_shading_in` |
| T-013 | Lux shading out | Drop lux below exit threshold | Return from shading; reason `lux_shading_out` |
| T-014 | Presence away forced open set | Switch presence to away | Amelie + Schlafzimmer (Fenster/Tuer) open even if normal morning open would not occur |
| T-015 | Presence home reaction | Switch presence to home | Presence policy action according to mode/time window |
| T-021 | Scale mapping 0..10 covers | Execute open/close/shade on EZ covers | Commands correctly denormalized to 0..10 range |
| T-022 | Global inversion behavior | Toggle global inversion in options and test one open/close cycle | All 9 shutters react consistently inverted/non-inverted |

## 4) Robustness and Edge Tests

| ID | Scenario | Steps | Expected |
| --- | --- | --- | --- |
| T-016 | HA restart during manual block | Start block, restart HA | Block state restored or safely re-established |
| T-017 | Sensor unavailable lux | Set lux sensor unavailable | Lux actions suppressed; no unsafe moves |
| T-018 | Sensor unavailable window | Set window sensor unavailable | Terrace special rule disabled with warning log |
| T-019 | Cover unavailable | Make one cover unavailable during command | Skip and log `cover_unavailable` |
| T-020 | Trigger burst/debounce | Fire rapid trigger sequence | Max one effective command per 30s per target position |

## 5) Acceptance Criteria (MVP)

1. All tests T-001..T-015 pass for pilot shutters.
2. Tests T-021 and T-022 pass before rollout beyond pilot.
3. At least 5 robustness tests (T-016..T-020) pass.
4. 7-day observer/active pilot with no critical wrong move.
5. Every executed or suppressed rule has reason code in logs.
6. No conflicting commands on same shutter within 30s.

## 6) Test Execution Log Template

| Date | Tester | Test ID | Result (pass/fail) | Evidence | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-10-09 | pilot | T-001 | pass | local decision trace: `astro_morning_open` | Morning-open gate verified in local dry-run |
| 2026-10-09 | pilot | T-008 | pass | manual-block decision trace | Auto shading suppressed while block active |
| 2026-10-09 | pilot | T-014 | pass | presence-away forced-open trace | Amelie and Schlafzimmer shutters opened as configured |
| YYYY-MM-DD | name | T-001 | pass | screenshot/log link | - |

## 7) Pilot Rollout Checklist

| Step | Status |
| --- | --- |
| Validate entity IDs | open |
| Enable ASC-lite only for 3 pilot shutters | open |
| Run observer mode for 2-3 days | open |
| Enable active mode | open |
| Monitor 7 days | open |
| Review incidents and tune thresholds | open |
| Approve rollout to remaining 6 shutters | open |

## 8) Out-of-Scope for MVP Testing

- Wind/rain safety automations (planned for v1.1+)
- Privacy mode semantics
- External triggers
- Full parity with every FHEM ASC edge behavior

Explicit MVP behavior constraints:

- Party mode affects terrace evening down only.
- Terrace has no lux shading behavior.

