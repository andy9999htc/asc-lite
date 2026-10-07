# ASC-lite MVP Decision Table

Status: Draft v1

## 1) Priority Order

Use this fixed order for every evaluation cycle:

1. Safety (future v1.1+)
2. Window/Ventilate protection
3. Party mode suppression
4. Manual block suppression
5. Presence gating
6. Astro open/close
7. Lux shading transitions
8. Fallback behavior

## 2) Rule Matrix

| Rule ID | Trigger | Preconditions | Blockers | Action | Reason code | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| R-WIN-001 | `fenster_wz_terrasse_contact -> on` | Auto enabled | none | Set `cover.rollladen_terrasse` to ventilate pos (55) | `terrace_window_open_ventilate` | 2 |
| R-WIN-002 | `fenster_wz_terrasse_contact -> off` | Auto enabled, party off | none | Allow normal rules again for terrace | `terrace_window_closed_resume` | 2 |
| R-PARTY-001 | party mode -> on | none | none | Suppress terrace evening down only | `party_mode_terrace_evening_down_suppress` | 3 |
| R-PARTY-002 | party mode -> off | Auto enabled | none | Resume terrace evening down rule | `party_mode_terrace_evening_down_resume` | 3 |
| R-MAN-001 | Cover position change | Internal command flag is off | none | Start manual block timer for this shutter | `manual_override_detected` | 4 |
| R-MAN-002 | Manual block active | any new auto shading/comfort action on same shutter | none | Skip drive for this shutter for shading/comfort actions only | `manual_block_active` | 4 |
| R-PRES-001 | presence -> away | Mode down for shutter is `always` or `absent` | party on, manual block for shading actions only | Close within down time window | `presence_away_close` | 5 |
| R-PRES-002 | presence -> away | shutter in `{Amelie_Fenster, Amelie_Tuer, Schlafzimmer_Fenster, Schlafzimmer_Tuer}` | manual block | Open even if normal morning open is not configured | `presence_away_forced_open` | 5 |
| R-PRES-003 | presence -> home | Mode up for shutter is `always` or `home` | manual block | Open within up time window | `presence_home_open` | 5 |
| R-ASTRO-001 | sun elevation crosses -6 (evening) | in down window, auto enabled | party on, manual block, terrace window open (terrace only) | Move to closed pos | `astro_evening_close` | 6 |
| R-ASTRO-002 | civil dawn (morning) | in up window, auto enabled | party on, manual block | Move to open pos | `astro_morning_open` | 6 |
| R-LUX-001 | lux above threshold with hysteresis | sun in azimuth range + temp gate pass, shutter is not terrace | manual block | Move to shading pos | `lux_shading_in` | 7 |
| R-LUX-002 | lux below threshold with hysteresis | currently shaded, shutter is not terrace | manual block | Return to day/open profile | `lux_shading_out` | 7 |
| R-FB-001 | adaptive state invalid | auto enabled | none | Do nothing, log and keep last stable state | `fallback_hold_state` | 8 |

## 3) Time Window Guard

| Guard | Definition |
| --- | --- |
| Up allowed | current time in `[Time_Up_Early, Time_Up_Late]` or weekend/holiday override value where configured |
| Down allowed | current time in `[Time_Down_Early, Time_Down_Late]` |
| Outside window | suppress the related up/down action and log `outside_time_window` |

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
| Party mode vs terrace evening close | Party mode suppresses terrace evening close only |
| Party mode vs all other shutters/rules | No suppression |
| Manual block vs shading/comfort actions | Manual block suppresses shading/comfort actions only |
| Manual block vs terrace evening down | Manual block does not suppress terrace evening down |
| Terrace window open vs evening close | Terrace window rule (ventilate)
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
| Should party mode suppress morning opens too? | no |
| Should presence away force close outside time window? | no for MVP |
| Should lux shading run when presence is away? | yes, unless explicitly disabled per shutter |
| Should terrace participate in lux shading? | no |
| Should entity IDs be hardcoded? | no, config-driven only |
| Does auto_enabled=off suppress all auto actions? | yes, including astro/shading/presence rules |
| Does manual block suppress evening-down actions? | no, manual block suppresses shading/comfort actions only; evening-down actions remain allowed for all shutters |
| Do we need privacy positions in MVP? | no (v1.1) |

