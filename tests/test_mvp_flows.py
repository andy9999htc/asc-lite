"""Pilot acceptance tests for the M4 stabilization phase.

These checks reflect the MVP flow expectations from the decision table and are
kept intentionally small and deterministic so they can be used as evidence for
pilot acceptance without requiring a full Home Assistant runtime.
"""

from __future__ import annotations

from custom_components.asc_lite.engine.astro import evaluate_astro_rule
from custom_components.asc_lite.engine.party import evaluate_party_rule
from custom_components.asc_lite.engine.position import denormalize_pct_to_native, normalize_native_to_pct
from custom_components.asc_lite.engine.presence import evaluate_presence_rule
from custom_components.asc_lite.engine.shading import evaluate_lux_shading
from custom_components.asc_lite.engine.state import StateSnapshot
from custom_components.asc_lite.engine.window import evaluate_window_protection


def test_scale_and_inversion_acceptance_for_pilot_shutters() -> None:
    """Scale conversion works for both 0..100 and 0..10 covers, with inversion support."""
    native_100 = normalize_native_to_pct(native_position=7, scale=100, invert=False)
    native_10 = normalize_native_to_pct(native_position=7, scale=10, invert=False)
    inverted_100 = normalize_native_to_pct(native_position=7, scale=100, invert=True)

    assert native_100 == 7.0
    assert native_10 == 70.0
    assert inverted_100 == 93.0
    assert denormalize_pct_to_native(percent_position=70.0, scale=10, invert=False) == 7
    assert denormalize_pct_to_native(percent_position=93.0, scale=100, invert=True) == 7


def test_terrace_window_and_party_rules_are_a_pilot_safe_sequence() -> None:
    """Terrace safety window protection remains active even when party mode is enabled."""
    terrace_cover = "cover.terrace"
    snapshot = StateSnapshot(
        {
            "binary_sensor.terrace_window": True,
            "input_boolean.asc_party_mode": True,
            terrace_cover: 72,
        }
    )

    window_decision = evaluate_window_protection(
        terrace_cover,
        snapshot,
        terrace_window_entity_id="binary_sensor.terrace_window",
        ventilate_position=35,
        terrace_cover_ids={terrace_cover},
    )
    party_decision = evaluate_party_rule(
        terrace_cover,
        snapshot,
        party_mode_entity_id="input_boolean.asc_party_mode",
        terrace_cover_ids={terrace_cover},
    )

    assert window_decision is not None
    assert window_decision.rule_id == "R-WIN-001"
    assert response_rate(window_decision.target_position) == 35
    assert party_decision is not None
    assert party_decision.rule_id == "R-PARTY-001"
    assert response_rate(party_decision.target_position) == 72


def test_presence_away_forced_open_set_matches_pilot_contract() -> None:
    """Away state opens the designated bedroom/child-room shutters even without morning logic."""
    cover = "cover.amelie_fenster"
    decision = evaluate_presence_rule(
        cover,
        StateSnapshot({"binary_sensor.resident_home": "away"}),
        presence_entity_id="binary_sensor.resident_home",
        home_values={"home", "on", "present"},
        away_values={"away", "off", "absent"},
        open_position=100,
        close_position=0,
        forced_open_cover_ids={cover},
    )

    assert decision is not None
    assert decision.rule_id == "R-PRES-002"
    assert decision.reason_code == "PRESENCE_AWAY_FORCED_OPEN"
    assert decision.target_position == 100


def test_astro_and_lux_rules_follow_pilot_gate_conditions() -> None:
    """Sun and lux decisions are accepted only when the configured window/gate conditions match."""
    astro = evaluate_astro_rule(
        "cover.wohnzimmer",
        StateSnapshot({"sun.sun": {"elevation": -7.0}}),
        sun_entity_id="sun.sun",
        close_elevation=-6,
        close_position=0,
        valid_cover_ids={"cover.wohnzimmer"},
    )
    lux = evaluate_lux_shading(
        "cover.wohnzimmer",
        StateSnapshot(
            {
                "sensor.lux_wz": 1200,
                "sun.sun": {"azimuth": 140, "elevation": 28},
                "sensor.outdoor_temp": 22,
            }
        ),
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
        current_position=0,
    )

    assert astro is not None
    assert astro.rule_id == "R-ASTRO-001"
    assert astro.target_position == 0
    assert lux is not None
    assert lux.rule_id == "R-LUX-001"
    assert lux.target_position == 35


def response_rate(value: int | float) -> int | float:
    """Normalize an integer target to a comparable numeric value for assertions."""
    return int(value)
