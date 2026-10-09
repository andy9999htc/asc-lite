"""Tests for the remaining M3 rule families: astro, presence, and lux shading."""

from __future__ import annotations

from custom_components.asc_lite.engine.astro import evaluate_astro_rule
from custom_components.asc_lite.engine.presence import evaluate_presence_rule
from custom_components.asc_lite.engine.shading import evaluate_lux_shading
from custom_components.asc_lite.engine.state import StateSnapshot


def test_evening_astro_close_activates_when_sun_below_horizon() -> None:
    snapshot = StateSnapshot({"sun.sun": {"elevation": -7}})

    decision = evaluate_astro_rule(
        "cover.terrace",
        snapshot,
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=0,
        valid_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-ASTRO-001"
    assert decision.reason_code == "ASTRO_EVENING_CLOSE"
    assert decision.target_position == 0


def test_presence_away_forced_open_set_opens_designated_cover() -> None:
    snapshot = StateSnapshot({"binary_sensor.resident_home": "away"})

    decision = evaluate_presence_rule(
        "cover.amelie_fenster",
        snapshot,
        presence_entity_id="binary_sensor.resident_home",
        away_values={"away", "off", "absent"},
        home_values={"home", "on", "present"},
        open_position=100,
        close_position=0,
        forced_open_cover_ids={"cover.amelie_fenster"},
    )

    assert decision is not None
    assert decision.rule_id == "R-PRES-002"
    assert decision.reason_code == "PRESENCE_AWAY_FORCED_OPEN"
    assert decision.target_position == 100


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
