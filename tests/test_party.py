"""Tests for the M3 party rule."""

from __future__ import annotations

from custom_components.asc_lite.engine.party import evaluate_party_rule
from custom_components.asc_lite.engine.state import StateSnapshot


def test_party_mode_blocks_terrace_evening_close_only() -> None:
    snapshot = StateSnapshot({"input_boolean.asc_party_mode": True, "cover.terrace": 80})

    decision = evaluate_party_rule(
        "cover.terrace",
        snapshot,
        party_mode_entity_id="input_boolean.asc_party_mode",
        terrace_cover_ids={"cover.terrace"},
    )

    assert decision is not None
    assert decision.rule_id == "R-PARTY-001"
    assert decision.reason_code == "PARTY_MODE"
    assert decision.target_position == 80


def test_party_mode_does_not_affect_other_covers() -> None:
    snapshot = StateSnapshot({"input_boolean.asc_party_mode": True, "cover.wohnzimmer": 80})

    decision = evaluate_party_rule(
        "cover.wohnzimmer",
        snapshot,
        party_mode_entity_id="input_boolean.asc_party_mode",
        terrace_cover_ids={"cover.terrace"},
    )

    assert decision is None


def test_party_mode_disabled_allows_normal_processing() -> None:
    snapshot = StateSnapshot({"input_boolean.asc_party_mode": False, "cover.terrace": 80})

    decision = evaluate_party_rule(
        "cover.terrace",
        snapshot,
        party_mode_entity_id="input_boolean.asc_party_mode",
        terrace_cover_ids={"cover.terrace"},
    )

    assert decision is None
