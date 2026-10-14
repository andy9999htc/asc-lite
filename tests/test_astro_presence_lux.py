"""Tests for the remaining M3 rule families: astro, presence, and lux shading."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.asc_lite.engine.astro import evaluate_astro_rule
from custom_components.asc_lite.engine.presence import evaluate_presence_rule
from custom_components.asc_lite.engine.shading import evaluate_lux_shading
from custom_components.asc_lite.engine.state import StateSnapshot


def test_evening_astro_close_activates_when_sun_below_horizon() -> None:
    snapshot = StateSnapshot({"sun.sun": {"next_setting": "2026-10-13T18:36:00+02:00"}})

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=0,
        current_datetime=datetime(2026, 10, 13, 18, 39, 33, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-001"
    assert decision.reason_code == "ASTRO_EVENING_CLOSE"
    assert decision.target_position == 0


def test_evening_astro_close_runs_when_cover_already_near_close_target() -> None:
    snapshot = StateSnapshot({"sun.sun": {"next_setting": "2026-10-13T18:36:00+02:00"}})

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=80,
        current_position=80,
        current_datetime=datetime(2026, 10, 13, 18, 39, 33, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-001"


def test_evening_astro_close_still_activates_when_not_near_close_target() -> None:
    snapshot = StateSnapshot({"sun.sun": {"next_setting": "2026-10-13T18:36:00+02:00"}})

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=80,
        current_position=35,
        current_datetime=datetime(2026, 10, 13, 18, 39, 33, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-001"
    assert decision.reason_code == "ASTRO_EVENING_CLOSE"
    assert decision.target_position == 80


def test_evening_astro_close_allows_within_sunset_grace_window() -> None:
    snapshot = StateSnapshot({"sun.sun": {"next_setting": "2026-10-13T17:00:00+00:00"}})

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=80,
        current_position=35,
        current_datetime=datetime(2026, 10, 12, 17, 10, tzinfo=timezone.utc),
        evening_close_grace_minutes=10,
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-001"


def test_evening_astro_close_skips_after_sunset_grace_window() -> None:
    snapshot = StateSnapshot({"sun.sun": {"next_setting": "2026-10-13T17:00:00+00:00"}})

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=80,
        current_position=35,
        current_datetime=datetime(2026, 10, 12, 17, 11, tzinfo=timezone.utc),
        evening_close_grace_minutes=10,
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is None


def test_evening_astro_close_skips_before_sunrise_even_when_elevation_is_low() -> None:
    snapshot = StateSnapshot(
        {
            "sun.sun": {
                "next_rising": "2026-10-13T07:44:00+02:00",
                "next_setting": "2026-10-13T18:36:00+02:00",
            }
        }
    )

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=20,
        current_position=100,
        current_datetime=datetime(2026, 10, 13, 6, 39, 33, tzinfo=timezone(timedelta(hours=2))),
        evening_close_grace_minutes=10,
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is None


def test_evening_astro_close_triggers_even_when_sun_is_above_close_elevation() -> None:
    snapshot = StateSnapshot(
        {
            "sun.sun": {
                "next_setting": "2026-10-13T18:36:00+02:00",
            }
        }
    )

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=20,
        current_position=100,
        current_datetime=datetime(2026, 10, 13, 18, 39, 33, tzinfo=timezone(timedelta(hours=2))),
        evening_close_grace_minutes=10,
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-001"
    assert decision.reason_code == "ASTRO_EVENING_CLOSE"
    assert decision.target_position == 20


def test_presence_away_forced_open_set_opens_designated_cover() -> None:
    snapshot = StateSnapshot({"binary_sensor.resident_home": "away"})

    decision = evaluate_presence_rule(
        "cover.amelie_fenster",
        snapshot,
        presence_entity_id="binary_sensor.resident_home",
        away_values={"away", "off", "absent"},
        open_position=100,
        forced_open_cover_ids={"cover.amelie_fenster"},
    )

    assert decision is not None
    assert decision.rule_id == "R-PRES-002"
    assert decision.reason_code == "PRESENCE_AWAY_FORCED_OPEN"
    assert decision.target_position == 100


def test_astro_morning_open_blocked_for_kids_when_presence_home() -> None:
    """When presence=home, astro morning open is blocked for kids shutters."""
    snapshot = StateSnapshot(
        {
            "sun.sun": {
                "next_rising": "2026-10-13T07:44:00+02:00",
                "next_setting": "2026-10-13T18:36:00+02:00",
            },
            "binary_sensor.resident_home": "on",
        }
    )

    decision = evaluate_astro_rule(
        "cover.amelie_fenster",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        current_datetime=datetime(2026, 10, 13, 7, 44, 30, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.amelie_fenster"},
        presence_entity_id="binary_sensor.resident_home",
        presence_home_values={"home", "on", "present"},
        presence_blocks_morning_open_for={"cover.amelie_fenster"},
    )

    assert decision is None


def test_astro_morning_open_allowed_for_kids_when_presence_away() -> None:
    """When presence=away, astro morning open is allowed for kids shutters."""
    snapshot = StateSnapshot(
        {
            "sun.sun": {
                "next_rising": "2026-10-13T07:44:00+02:00",
                "next_setting": "2026-10-13T18:36:00+02:00",
            },
            "binary_sensor.resident_home": "away",
        }
    )

    decision = evaluate_astro_rule(
        "cover.amelie_fenster",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        current_datetime=datetime(2026, 10, 13, 7, 44, 30, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.amelie_fenster"},
        presence_entity_id="binary_sensor.resident_home",
        presence_home_values={"home", "on", "present"},
        presence_blocks_morning_open_for={"cover.amelie_fenster"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-002"
    assert decision.reason_code == "ASTRO_MORNING_OPEN"
    assert decision.target_position == 100


def test_astro_morning_open_triggers_even_when_sun_is_below_open_elevation() -> None:
    snapshot = StateSnapshot(
        {
            "sun.sun": {
                "elevation": -3.5,
                "next_rising": "2026-10-13T07:44:00+02:00",
                "next_setting": "2026-10-13T18:36:00+02:00",
            },
            "binary_sensor.resident_home": "away",
        }
    )

    decision = evaluate_astro_rule(
        "cover.amelie_fenster",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        close_position=0,
        current_position=0,
        current_datetime=datetime(2026, 10, 13, 7, 44, 30, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.amelie_fenster"},
        presence_entity_id="binary_sensor.resident_home",
        presence_home_values={"home", "on", "present"},
        presence_blocks_morning_open_for={"cover.amelie_fenster"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-002"
    assert decision.reason_code == "ASTRO_MORNING_OPEN"
    assert decision.target_position == 100


def test_astro_morning_open_runs_when_cover_not_closed() -> None:
    """Astro open should run in the morning window, even from intermediate positions."""
    snapshot = StateSnapshot({"sun.sun": {"next_rising": "2026-10-13T07:44:00+02:00", "next_setting": "2026-10-13T18:36:00+02:00"}})

    decision = evaluate_astro_rule(
        "cover.wohnzimmer",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        close_position=0,
        current_position=60,
        current_datetime=datetime(2026, 10, 13, 7, 44, 30, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.wohnzimmer"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-002"


def test_astro_morning_open_custom_close_position_runs_for_intermediate_position() -> None:
    snapshot = StateSnapshot({"sun.sun": {"next_rising": "2026-10-13T07:44:00+02:00", "next_setting": "2026-10-13T18:36:00+02:00"}})

    already_open_decision = evaluate_astro_rule(
        "cover.wohnzimmer",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        close_position=80,
        current_position=100,
        current_datetime=datetime(2026, 10, 13, 7, 44, 30, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.wohnzimmer"},
    )

    run_decision = evaluate_astro_rule(
        "cover.wohnzimmer",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        close_position=80,
        current_position=35,
        current_datetime=datetime(2026, 10, 13, 7, 44, 30, tzinfo=timezone(timedelta(hours=2))),
        valid_cover_ids={"cover.wohnzimmer"},
    )

    assert already_open_decision is not None
    assert already_open_decision.rule_id == "R-ASTRO-002"
    assert run_decision is not None
    assert run_decision.rule_id == "R-ASTRO-002"


def test_astro_morning_open_skips_after_sunrise_grace_window() -> None:
    snapshot = StateSnapshot(
        {"sun.sun": {"elevation": 10, "next_rising": "2026-10-13T05:00:00+00:00", "next_setting": "2026-10-13T17:00:00+00:00"}}
    )

    decision = evaluate_astro_rule(
        "cover.wohnzimmer",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        close_position=80,
        current_position=80,
        current_datetime=datetime(2026, 10, 12, 5, 11, tzinfo=timezone.utc),
        morning_open_grace_minutes=10,
        valid_cover_ids={"cover.wohnzimmer"},
    )

    assert decision is None


def test_astro_morning_open_allows_within_sunrise_grace_window() -> None:
    snapshot = StateSnapshot(
        {"sun.sun": {"elevation": 10, "next_rising": "2026-10-13T05:00:00+00:00", "next_setting": "2026-10-13T17:00:00+00:00"}}
    )

    decision = evaluate_astro_rule(
        "cover.wohnzimmer",
        snapshot,
        sun_entity_id="sun.sun",
        open_elevation=0,
        open_position=100,
        close_position=80,
        current_position=80,
        current_datetime=datetime(2026, 10, 12, 5, 10, tzinfo=timezone.utc),
        morning_open_grace_minutes=10,
        valid_cover_ids={"cover.wohnzimmer"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-002"


def test_lux_shading_in_moves_non_terrace_cover_to_shading_position() -> None:
    snapshot = StateSnapshot(
        {
            "sensor.lux_wz": 1200,
            "sun.sun": {"azimuth": 140, "elevation": 28},
            "sensor.outdoor_temp": 22,
        }
    )

    decision = evaluate_lux_shading(
        "cover.wohnzimmer",
        snapshot,
        lux_entity_id="sensor.lux_wz",
        sun_entity_id="sun.sun",
        temp_entity_id="sensor.outdoor_temp",
        azimuth_min=90,
        azimuth_max=180,
        elevation_min=0,
        elevation_max=65,
        min_temp_c=18,
        enter_lux=400,
        shading_position=35,
        restore_position=80,
        non_terrace_cover_ids={"cover.wohnzimmer"},
    )

    assert decision is not None
    assert decision.rule_id == "R-LUX-001"
    assert decision.reason_code == "LUX_SHADING_IN"
    assert decision.target_position == 35


def test_lux_shading_out_returns_cover_to_day_position() -> None:
    snapshot = StateSnapshot(
        {
            "sensor.lux_wz": 180,
            "sun.sun": {"azimuth": 140, "elevation": 28},
            "sensor.outdoor_temp": 22,
        }
    )

    decision = evaluate_lux_shading(
        "cover.wohnzimmer",
        snapshot,
        lux_entity_id="sensor.lux_wz",
        sun_entity_id="sun.sun",
        temp_entity_id="sensor.outdoor_temp",
        azimuth_min=90,
        azimuth_max=180,
        elevation_min=0,
        elevation_max=65,
        min_temp_c=18,
        enter_lux=400,
        exit_lux=300,
        shading_position=35,
        restore_position=80,
        non_terrace_cover_ids={"cover.wohnzimmer"},
        current_position=35,
    )

    assert decision is not None
    assert decision.rule_id == "R-LUX-002"
    assert decision.reason_code == "LUX_SHADING_OUT"
    assert decision.target_position == 80
