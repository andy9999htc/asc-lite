# Pflichtenheft: ASC-lite als Home Assistant HACS Integration

Status: Draft v1 (auf Basis der aktuellen `fhem.cfg` und `rollladen_asc_inventory.md`)

## 1. Zielbild

Ziel ist eine eigene Python-basierte HA-Integration (`custom_components/asc_lite`), die den fuer dein Haus relevanten FHEM-ASC-Funktionsumfang ohne umfangreiche Wrapper-Skriptlandschaft abbildet.

Wichtig: Es geht bewusst um ASC-lite fuer dein Setup, nicht um 100% Feature-Paritaet zum kompletten FHEM-Modul.

## 2. Scope

### In Scope (MVP bis v1.0)

- Steuerung von 9 DuoFern-Covern:
  - Rollladen_Wohnzimmer
  - Rollladen_Terrasse
  - Rollladen_Amelie_Fenster
  - Rollladen_Amelie_Tuer
  - Rollladen_Schlafzimmer_Fenster
  - Rollladen_Schlafzimmer_Tuer
  - Rollladen_EZ_links
  - Rollladen_EZ_mitte
  - Rollladen_EZ_rechts
- Astro-Morgen/Abend mit globalen Defaults:
  - `ASC_autoAstroModeMorning = CIVIL`
  - `ASC_autoAstroModeEvening = HORIZON`
  - `ASC_autoAstroModeEveningHorizon = -6`
- Zeitfenster pro Shutter (`Time_Up_*`, `Time_Down_*`)
- Lux/Shading-Kernlogik (inkl. Hysterese)
- Presence-Gating (`dmy_Resident` aehnlich home/away)
- Party-Mode nur fuer Terrasse-Abendfahrt (unterdrueckt nur das abendliche Runterfahren der Terrasse)
- Manual override lockout pro Shutter (Timer-basiert)
- Fensterkontakt-Logik fuer Terrasse (`Fenster_WZ_Terrasse` + Ventilate-Position)
- Beobachtbarkeit/Diagnostik (Statussensoren, letzter Fahrgrund, Blockierstatus)
- Konfigurationsgetriebene Entity IDs (keine hardcodierten HA Entity IDs im Code)
- Einheitliche Positionsrichtung fuer alle Rolllaeden (`0=open`, `10/100=closed`) mit gemischter Skala (0..100 und 0..10)

### Out of Scope (v1)

- Vollstaendige FHEM-API-Paritaet (`ascAPIget/set` komplett)
- Exotische Spezialfaelle aller ASC-Attribute, die in deinem Bestand nicht genutzt werden
- Komplettes Re-Design der HA-Cover-Entitaeten
- UI-Perfektion im ersten Wurf

## 3. Muss-/Soll-/Kann Anforderungen

### Muss (MVP)

1. Deterministische Prioritaetslogik fuer Befehle:
   - Safety > Fenster/Ventilate > Party/Presence > Astro/Lux > Fallback
2. Wenn `auto_enabled` auf `off` steht, werden alle Auto-Aktionen unterdrueckt; nur manuelle Fahrbefehle bleiben erlaubt.
3. Manual-Block unterdrueckt nur Shading-/Comfort-Autoaktionen des betroffenen Shutters, aber nicht die Abendrunterfahrt aller Rolllaeden bzw. die durch Safety/Window-Regeln ausgelösten Fahrbefehle.
4. Korrekte Behandlung von Invertierung/Positionssemantik je Cover.
5. Restart-sicher:
   - Letzter Zustand und aktive Block-Timer werden wiederhergestellt.
6. Konfliktfreie Parallelitaet:
   - Keine Doppelkommandos bei schnellen Sensorwechseln.
7. Konfigurierbar via Config/Options Flow (ohne YAML-Pflicht).
8. Keine Gruppenlogik im MVP; alle relevanten Policies werden pro Shutter konfiguriert.
9. Erweiterte Shading-Fenster:
   - Azimuth, Elevation, Min-Temp, Lux-Hysterese pro Shutter / Config-Entry.
10. Gesteuerte Degradation:
   - Bei fehlendem Sensor keine Fehlfahrt, sondern definierter Fallback.

### Kann (v1.2+)

1. Wind-/Rain-Schutz als native Policy.
2. External Trigger (TV, Alarm, etc.).
3. Teilweise FHEM-API-Kompatibilitaets-Layer (diagnostisch).

## 4. Feature-Mapping aus deinem Bestand

| FHEM-Feature/Attribut | Nutzung im Bestand | ASC-lite Umsetzung | Prioritaet |
| --- | --- | --- | --- |
| `ASC_autoAstroModeMorning=CIVIL` | global gesetzt | Astro open policy | Must |
| `ASC_autoAstroModeEvening=HORIZON`, `...Horizon=-6` | global gesetzt | Astro close policy | Must |
| `ASC_brightnessDriveUpDown=400:400` | global gesetzt | Lux threshold baseline | Must |
| `ASC_residentsDev=dmy_Resident` | global gesetzt | Presence provider | Must |
| `ASC_Time_Up_*`, `ASC_Time_Down_*` | alle Shutter | Time window guards | Must |
| `ASC_Shading_*` | breit genutzt | Shading engine pro Shutter, ohne Gruppenmodell | Must |
| `ASC_Ventilate_Pos` | alle Shutter | Ventilate target | Must |
| `ASC_WindowRec` (Terrasse) | gesetzt | Window inhibit + ventilate | Must |
| `ASC_BlockingTime_afterManual` | teils explizit | Manual lock timer (default + override) | Must |
| `ASC_Mode_Up/Down` | alle Shutter | Presence gate policy | Should |
| Presence-away Sonderregel | Amelie + Schlafzimmer Fenster/Tuer | Forced open policy on away | Must |
| `ASC_ComfortOpen_Pos` / `ASC_PrivacyDown_Pos` | alle Shutter | Komfort-/Privacy profile | Should |
| `ASC_WindProtection` / `ASC_RainProtection` | vorhanden, nicht priorisiert | Safety policy module | Could |
| `ASC_ExternalTrigger` | vorgesehen in ASC, lokal nicht Kern | Event hook framework | Could |

## 5. Zielarchitektur (HA)

`custom_components/asc_lite/`

- `manifest.json`
- `__init__.py`
- `config_flow.py` (setup + options)
- `coordinator.py` (zentrale State-Machine + Scheduler)
- `models.py` (ShutterConfig, PolicyConfig)
- `engine/`
  - `priority.py` (Regelprioritaeten)
  - `astro.py`
  - `shading.py`
  - `presence.py`
  - `window.py`
  - `manual.py`
- `entities/`
  - diagnostics sensors
  - switches (`auto_enabled`, `party_mode`, optional group toggles)
- `services.yaml`
  - `asc_lite.force_open`, `force_close`, `set_party_mode`, `set_manual_block`

## 6. Nicht-funktionale Anforderungen

1. Latenz: Entscheidungszyklus < 1s bei Trigger-Ereignis.
2. Stabilitaet: Keine Endlosschleifen/Flap bei Sensor-Jitter.
3. Testbarkeit:
   - Unit-Tests fuer Policy-Matrix
   - Integrationstests fuer zentrale Szenarien
4. Wartbarkeit:
   - Klare Trennung Sensor-Ingest, Policy-Decision, Command-Dispatch.

## 7. Testkatalog (MVP)

### Kritische Szenarien

1. Abendfahrt bei Sonnenhoehe -6 innerhalb Zeitfenster.
2. Morgenfahrt CIVIL innerhalb Zeitfenster.
3. Fenster Terrasse offen waehrend Schliesslogik -> nur Ventilate.
4. Manuelle Fahrt -> Block aktiv -> naechste Auto-Fahrt wird unterdrueckt.
5. Party-Mode ON -> regulare Abendfahrt ausgesetzt.
6. Presence wechselt auf away -> definierte Aktion ohne Konflikt.
7. Neustart waehrend Blocktimer -> Block bleibt korrekt aktiv.

### Abnahmekriterien

- 7 Tage Dual-Run ohne Fehlfahrt in den Pilot-Shuttern:
  - Rollladen_Wohnzimmer
  - Rollladen_Terrasse
  - Rollladen_EZ_links
- Keine gegensaetzlichen Fahrkommandos innerhalb von 30s auf demselben Shutter.
- Jede Fahrt hat einen eindeutig protokollierten Grund (`reason code`).

## 8. Migrationsreihenfolge

### Phase A (2-4 Wochen): MVP Pilot

- Pilot nur 3 Shutter: WZ, Terrasse, EZ_links
- Features: Astro + TimeWindow + WindowProtection + ManualBlock + Party + Basic Shading

### Phase B (2-3 Wochen): Ausbau auf 9 Shutter

- Rollout auf restliche 6 Shutter
- Feintuning pro Raum/Azimuth/Lux

### Phase C (2-4 Wochen): Produktivhaertung

- Diagnostics vervollstaendigen
- Edge-Case-Fixes
- Optionen/UX in Config Flow
- HACS-Releaseprozess

## 9. Aufwandsschaetzung

Realistische Schaetzung fuer 1 erfahrenen Entwickler:

- ASC-lite MVP (dein Setup): 4-8 Wochen
- Stabiler Hausbetrieb + HACS-tauglich: 8-14 Wochen
- Nahe FHEM-Paritaet: 4-8 Monate

Hauptkostentreiber:

- Event-/Timer-Semantik und Prioritaetskonflikte
- Robustheit bei manuellen Fahrten und Sensorflattern
- Restart-Safety + Tests

## 10. Entscheidungsgrundlage (Build vs. Hybrid)

### Build ASC-lite ist sinnvoll, wenn

- du langfristig 1 integriertes, eigenes Regelwerk willst,
- und initialen Implementationsaufwand akzeptierst.

### Hybrid (Adaptive Cover + leichte Wrapper) ist sinnvoll, wenn

- du schneller zu stabilen Ergebnissen willst,
- und den groessten Teil der Kernlogik bereits vorhanden nutzen moechtest.

## 11. Konkrete Empfehlung fuer dich

1. Starte mit ASC-lite MVP nur fuer 3 Pilot-Shutter.
2. Behalte Adaptive-Cover-Setup als Fallback waehrend Pilotphase.
3. Entscheide nach 2 Wochen realem Pilotbetrieb:
   - Wenn stabil: Vollausbau ASC-lite.
   - Wenn nicht stabil: Hybrid dauerhaft beibehalten.

## 12. Festgelegte Architekturentscheidungen (verbindlich)

1. Entity IDs werden ausschliesslich ueber Config Flow / Options konfiguriert, nicht hardcodiert.
2. `auto_enabled` auf `off` unterdrueckt alle Auto-Aktionen; nur manuelle Fahrbefehle bleiben erlaubt.
3. Party-Mode gilt nur fuer Terrasse und nur fuer die Abendfahrt (Down).
4. Manual-Block unterdrueckt nur Shading-/Comfort-Autoaktionen; die Abendrunterfahrt aller Rolllaeden bleibt erlaubt, auch wenn der Shutter gerade manuell blockiert ist.
5. Presence-away darf Amelie und Schlafzimmer (Fenster + Tuer) explizit oeffnen.
6. Alle Rolllaeden haben gleiche Richtung (`0=open`), aber zwei Skalen:
   - 6 Rolllaeden: 0..100
   - 3 Esszimmer-Rolllaeden: 0..10
   Interne Logik arbeitet normalisiert auf 0..100.

---

## Anhang A: Aktuelle Device-Basis

Referenz: `fhem/docs/rollladen_asc_inventory.md`

- Gesamt: 9 DUOFERN-Rolllaeden
- Global relevant: `CIVIL`, `HORIZON -6`, `400:400`, `dmy_Resident`
- Terrasse-Sonderlogik vorhanden (`ASC_WindowRec Fenster_WZ_Terrasse`)
- Manuelle Blockzeit explizit bei EZ_mitte/EZ_rechts auf 14400
