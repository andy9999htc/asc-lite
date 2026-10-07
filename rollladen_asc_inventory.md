# Rollladen ASC Inventory

Source: [`/home/pi/fhem/myfhem/fhem/fhem.cfg`](../fhem.cfg)

This file lists only explicit ASC-relevant attributes found in `fhem.cfg` for the DUOFERN roller shutters. Empty cells mean the attribute was not explicitly set in the config excerpt I parsed.

## Global ASC Controller

| Device | ASC_autoAstroModeMorning | ASC_autoAstroModeEvening | ASC_autoAstroModeEveningHorizon | ASC_brightnessDriveUpDown | ASC_residentsDev |
| --- | --- | --- | --- | --- | --- |
| Rollladenautomatik | CIVIL | HORIZON | -6 | 400:400 | dmy_Resident |

## Rollladen Devices

| Device | Alias | Room | ASC | ASC_Down | ASC_Mode_Up | ASC_Mode_Down | ASC_Closed_Pos | ASC_ComfortOpen_Pos | ASC_Open_Pos | ASC_Partymode | ASC_Shading_Mode | ASC_Shading_Pos | ASC_Shading_InOutAzimuth | ASC_Shading_Min_OutsideTemperature | ASC_Shading_StateChange_SunnyCloudy | ASC_Time_Up_Early | ASC_Time_Up_Late | ASC_Time_Up_WE_Holiday | ASC_Time_Down_Early | ASC_Time_Down_Late | ASC_Ventilate_Pos | ASC_Ventilate_Window_Open | ASC_BrightnessSensor | ASC_BlockingTime_afterManual | ASC_WindowRec |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Rollladen_Wohnzimmer | Rollladen Wohnzimmer | DUOFERN,Wohnzimmer | 1 | astro | always | always | 80 | 50 | 0 | off | always | 35 | 100:245 | 19 | 31000:20000 | 06:15 | 09:00 | 08:00 | 16:30 | 22:00 | 70 | - | BWM_WZ_Presence:illuminance1 400:400 | - | - |
| Rollladen_Terrasse | Rollladen Terrasse | DUOFERN,Wohnzimmer | 1 | astro | always | always | 80 | 50 | 0 | off | - | 35 | - | - | - | 06:15 | 09:00 | 08:00 | 16:30 | 22:15 | 55 | off | BWM_WZ_Presence:illuminance1 400:400 | - | Fenster_WZ_Terrasse |
| Rollladen_Amelie_Fenster | Rollladen Amelie Fenster | DUOFERN,Kind_Amelie | 1 | - | absent | always | 99 | 50 | 0 | off | always | 60 | 80:155 | 19 | 25000:18000 | 07:45 | 09:30 | 09:30 | 16:30 | 22:00 | 60 | - | BWM_EZ_Presence:illuminance1 400:400 | - | - |
| Rollladen_Amelie_Tuer | Rollladen Amelie Tür | DUOFERN,Kind_Amelie | 1 | - | absent | always | 99 | 50 | 0 | off | always | 55 | 80:155 | 19 | 25000:18000 | 07:45 | 09:30 | 09:30 | 16:30 | 22:00 | 55 | - | BWM_EZ_Presence:illuminance1 400:400 | - | - |
| Rollladen_Schlafzimmer_Fenster | Rollladen Leonard Fenster | DUOFERN,Kind_Leonard | 1 | - | absent | always | 99 | 50 | 0 | off | always | 60 | 80:155 | 19 | 25000:18000 | 08:30 | 09:30 | 09:30 | 16:30 | 22:00 | 60 | - | BWM_EZ_Presence:illuminance1 400:400 | - | - |
| Rollladen_Schlafzimmer_Tuer | Rollladen Lenoard Tür | DUOFERN,Kind_Leonard | 1 | - | absent | always | 99 | 35 | 0 | off | always | 55 | 80:155 | 19 | 25000:18000 | 08:30 | 09:30 | 09:30 | 16:30 | 22:00 | 35 | - | BWM_EZ_Presence:illuminance1 400:400 | - | - |
| Rollladen_EZ_links | Rollladen Esszimmer links | DUOFERN,Esszimmer | 1 | astro | always | always | 10 | 5 | 0 | off | absent | 6 | 75:155 | 20 | 38000:20000 | 05:58 | 09:30 | 08:00 | 16:30 | 22:00 | 7 | off | BWM_EZ_Presence:illuminance1 400:600 | - | - |
| Rollladen_EZ_mitte | Rollladen Esszimmer mitte | DUOFERN,Esszimmer | 1 | astro | always | always | 9 | 5 | 0 | off | always | 6 | 75:155 | 19 | 25000:18000 | 05:58 | 09:30 | 08:00 | 16:30 | 22:00 | 7 | off | BWM_EZ_Presence:illuminance1 400:600 | 14400 | - |
| Rollladen_EZ_rechts | Rollladen Esszimmer rechts | DUOFERN,Esszimmer | 1 | astro | always | always | 9 | 5 | 0 | off | always | 7 | 75:155 | 19 | 25000:18000 | 05:58 | 09:30 | 08:00 | 16:30 | 22:00 | 7 | off | BWM_EZ_Presence:illuminance1 400:600 | 14400 | - |

## Notes

- The `ASC` column is `1` for every listed shutter.
- `-` means no explicit attribute value was present in the current `fhem.cfg` excerpt.
- `ASC_Down` is only explicitly set on the Wohnzimmer, Terrasse, and Esszimmer shutters shown above.
- `ASC_BlockingTime_afterManual` is explicitly set to `14400` only on `Rollladen_EZ_mitte` and `Rollladen_EZ_rechts` in the current config.
