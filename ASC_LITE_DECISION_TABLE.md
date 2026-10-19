# ASC-lite MVP Decision Table

Status: Runtime-aligned (v0.6.10+)

## 1) Priority Order

Use this fixed order for every evaluation cycle:

1. Safety (future v1.1+)
2. Party mode suppression
3. Manual block suppression
4. Presence gating (kids forced open when away only; blocks astro morning open when home)
5. Astro open/close
6. Lux shading transitions
7. Fallback behavior

## 2) Rule Matrix

| Rule ID | Trigger | Preconditions | Blockers | Action | Reason code | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| R-PARTY-001 | party mode is truthy (`on/open/true`) | cover is terrace cover | none | Hold terrace at current position (suppresses following terrace rules in that cycle) | `PARTY_MODE` | 2 |
| R-MAN-001 | Cover position change | Internal command flag is off | none | Start manual block timer for this shutter | `manual_override_detected` | 3 |
| R-MAN-002 | Manual block active | decision in `{R-LUX-001, R-LUX-002, R-ASTRO-002}` | none | Skip dispatch for this shutter | `MANUAL_BLOCK_ACTIVE` | 3 |
| R-PRES-002 | presence in `{away, off, absent}` | shutter in `{amelie_fenster, amelie_tuer, schlafzimmer_fenster, schlafzimmer_tuer}` | manual block (dispatch-time) | Open even if normal morning open is not configured | `PRESENCE_AWAY_FORCED_OPEN` | 4 |
| R-ASTRO-001 | current time in sunset window | auto enabled | terrace blockers by precedence (`R-PARTY-001`), once/day runtime guard | Move to configured close position | `ASTRO_EVENING_CLOSE` | 5 |
| R-ASTRO-002 | current time in morning-open window (weekend fixed time if configured, otherwise sunrise window) | auto enabled | presence=home for kids, manual block (dispatch-time), terrace blockers by precedence (`R-PARTY-001`), once/day runtime guard | Move to open position (100) | `ASTRO_MORNING_OPEN` | 5 |
| R-LUX-001 | lux >= enter threshold | sun in azimuth/elevation range, temp gate pass, shutter is not terrace | manual block (dispatch-time) | Move to shading position | `LUX_SHADING_IN` | 6 |
| R-LUX-002 | lux <= exit threshold while currently shaded | shutter is not terrace | manual block (dispatch-time) | Return to day/open profile | `LUX_SHADING_OUT` | 6 |

## 3) Time Window Guard

| Guard | Definition |
| --- | --- |
| Morning up allowed (`R-ASTRO-002`) | Weekdays: `current_datetime` in `[sun.next_rising, sun.next_rising + 10 minutes]` (with sunrise anchor correction when HA already points `next_rising` to tomorrow). Weekends: if cover has `morning_open_weekend_time`, use `[fixed_time, fixed_time + 10 minutes]` in local time. |
| Evening down allowed (`R-ASTRO-001`) | `current_datetime` in `[sun.next_setting, sun.next_setting + 10 minutes]` (with sunset anchor correction when HA already points `next_setting` to tomorrow) |
| Outside window | astro rule does not match in that cycle |

## 3.1) Astro Once-Per-Day Guard

Runtime applies an additional suppression guard per cover and astro rule:

- Key: `(cover_id, rule_id)` for `R-ASTRO-001` and `R-ASTRO-002`
- Scope: current local calendar day
- Behavior: if already executed today, decision is suppressed with reason code `ASTRO_ALREADY_EXECUTED_TODAY`

## 4) Per-Shutter Shading Config (MVP)

Die Shading-Policy wird nicht gruppenbasiert modelliert. Jeder Shutter hat seine eigenen Werte fuer:

- `azimuth_min`, `azimuth_max`
- `elevation_min` / `elevation_max`
- `min_temp_c`
- `lux_enter`
- `lux_exit`
- `hysteresis_enabled` (bool)

| Shutter | Azimuth | Elevation | Min Temp | Enter lux | Exit lux |
| --- | --- | --- | --- | --- | --- |
| configurable per shutter | configurable per shutter | configurable per shutter | configurable per shutter | configurable per shutter | configurable per shutter |

Note:
- Diese Werte sind Initialwerte aus der FHEM-ASC-Logik und werden in der Pilotphase per Shutter konkretisiert.
- Gruppenlogik ist im MVP nicht erforderlich und bewusst nicht Teil der Implementierung.

## 5) Conflict Resolution

| Conflict | Winner |
| --- | --- |
| Party mode vs terrace rules | Party rule wins by priority and keeps current terrace position |
| Party mode vs non-terrace rules | No suppression |
| Manual block vs shading/comfort actions | Manual block suppresses shading/comfort actions only |
| Manual block vs terrace evening down (`R-ASTRO-001`) | Manual block does not suppress evening-down |
| Terrace window open vs evening close | No special terrace window rule remains; standard evening close behavior applies.
| Presence action vs lux action in same cycle | Presence action first, lux re-evaluates next cycle |

## 6) Decision Logging Contract

Each attempted decision should emit:

- shutter
- trigger
- evaluated_rule_id
- result (`executed`, `suppressed`, `skipped`)
- reason_code
- target_position (if executed)

## 7) Open Questions Before Coding

| Question | Current assumption |
| --- | --- |
| Should party mode suppress morning opens too? | currently yes for terrace due `R-PARTY-001` precedence/hold behavior |
| Should presence away force close outside time window? | no for MVP |
| Should lux shading run when presence is away? | yes, unless explicitly disabled per shutter |
| Should terrace participate in lux shading? | no |
| Should entity IDs be hardcoded? | no, config-driven only |
| Does auto_enabled=off suppress all auto actions? | yes, including astro/shading/presence rules |
| Does manual block suppress evening-down actions? | no, manual block suppresses shading/comfort actions only; evening-down actions remain allowed for all shutters |
| Do we need privacy positions in MVP? | no (v1.1) |

