"""Tests for the M1 priority and state snapshot layers."""

from __future__ import annotations

from custom_components.asc_lite.engine.priority import Decision, PriorityRule, evaluate_rules
from custom_components.asc_lite.engine.state import StateSnapshot, build_state_snapshot


def test_priority_rules_select_highest_priority_match() -> None:
    rules: list[PriorityRule] = [
        PriorityRule(
            rule_id="R-LOW",
            priority=10,
            reason_code="LOW",
            predicate=lambda snapshot: snapshot.get("sun.sun") == "night",
            action=lambda snapshot: Decision(rule_id="R-LOW", reason_code="LOW", target_position=0),
        ),
        PriorityRule(
            rule_id="R-HIGH",
            priority=50,
            reason_code="HIGH",
            predicate=lambda snapshot: snapshot.get("presence") == "home",
            action=lambda snapshot: Decision(rule_id="R-HIGH", reason_code="HIGH", target_position=80),
        ),
    ]

    snapshot = StateSnapshot({"sun.sun": "night", "presence": "home"})
    decision = evaluate_rules(snapshot, rules)

    assert decision is not None
    assert decision.rule_id == "R-HIGH"
    assert decision.reason_code == "HIGH"
    assert decision.target_position == 80


def test_priority_rules_are_deterministic_for_equal_priority() -> None:
    rules: list[PriorityRule] = [
        PriorityRule(
            rule_id="R-B",
            priority=20,
            reason_code="B",
            predicate=lambda snapshot: True,
            action=lambda snapshot: Decision(rule_id="R-B", reason_code="B", target_position=10),
        ),
        PriorityRule(
            rule_id="R-A",
            priority=20,
            reason_code="A",
            predicate=lambda snapshot: True,
            action=lambda snapshot: Decision(rule_id="R-A", reason_code="A", target_position=20),
        ),
    ]

    snapshot = StateSnapshot({"presence": "home"})
    decision = evaluate_rules(snapshot, rules)

    assert decision is not None
    assert decision.rule_id == "R-A"
    assert decision.target_position == 20


def test_state_snapshot_uses_fallbacks_for_missing_or_unavailable_states() -> None:
    snapshot = build_state_snapshot(
        {
            "sensor.temp": 18.0,
            "binary_sensor.terrace_window": "unavailable",
            "cover.rollladen": None,
        },
        defaults={
            "binary_sensor.terrace_window": False,
            "cover.rollladen": 0,
            "binary_sensor.missing": True,
        },
    )

    assert snapshot.get("sensor.temp") == 18.0
    assert snapshot.get("binary_sensor.terrace_window") is False
    assert snapshot.get("cover.rollladen") == 0
    assert snapshot.get("binary_sensor.missing") is True


def test_state_snapshot_accepts_dict_like_states_without_crashing() -> None:
    snapshot = build_state_snapshot(
        {"sun.sun": {"elevation": -7.0, "azimuth": 160}, "sensor.lux": 650},
        defaults={"sun.sun": {"elevation": 0.0, "azimuth": 0}, "sensor.lux": 0},
    )

    assert snapshot.get("sun.sun") == {"elevation": -7.0, "azimuth": 160}
    assert snapshot.get("sensor.lux") == 650


def test_state_snapshot_uses_known_values_without_fallback() -> None:
    snapshot = StateSnapshot({"sensor.lux": 650, "cover.1": 40})

    assert snapshot.get("sensor.lux") == 650
    assert snapshot.get("cover.1") == 40
    assert snapshot.get("sensor.missing", default=999) == 999
