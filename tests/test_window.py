"""Tests for the M3 terrace window protection rule."""

from __future__ import annotations

from custom_components.asc_lite.engine.state import StateSnapshot
from custom_components.asc_lite.engine.window import evaluate_window_protection


def test_terrace_window_open_for_terrace_cover_uses_ventilate_position() -> None:
    snapshot = StateSnapshot({"binary_sensor.terrace_window": True})

    decision = evaluate_window_protection(
        "cover.terrace",
        snapshot,
        terrace_window_entity_id="binary_sensor.terrace_window",
        ventilate_position=35,
        terrace_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-WIN-001"
    assert decision.reason_code == "WINDOW_OPEN"
    assert decision.target_position == 35


def test_terrace_window_closed_does_not_trigger_rule() -> None:
    snapshot = StateSnapshot({"binary_sensor.terrace_window": False})

    decision = evaluate_window_protection(
        "cover.terrace",
        snapshot,
        terrace_window_entity_id="binary_sensor.terrace_window",
        ventilate_position=35,
        terrace_cover_ids={"cover.terrace"},
    )

    assert decision is None


def test_non_terrace_cover_is_not_affected_by_window_rule() -> None:
    snapshot = StateSnapshot({"binary_sensor.terrace_window": True})

    decision = evaluate_window_protection(
        "cover.wohnzimmer",
        snapshot,
        terrace_window_entity_id="binary_sensor.terrace_window",
        ventilate_position=35,
        terrace_cover_ids={"cover.terrace"},
    )

    assert decision is None
