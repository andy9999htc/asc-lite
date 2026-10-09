"""Tests for the M2 diagnostic sensor and switch helpers."""

from __future__ import annotations

from custom_components.asc_lite.sensor import build_diagnostic_sensor_values
from custom_components.asc_lite.switch import build_switch_descriptors


def test_diagnostic_sensor_values_are_stable_and_human_readable() -> None:
    sensors = build_diagnostic_sensor_values(
        cover_id="cover.rollladen_wohnzimmer",
        last_decision_rule="R-HIGH",
        last_decision_reason="HIGH",
        manual_block_active=True,
    )

    assert sensors["last_decision_rule"] == "R-HIGH"
    assert sensors["last_decision_reason"] == "HIGH"
    assert sensors["manual_block_active"] is True


def test_switch_descriptors_include_optional_auto_and_party_switches() -> None:
    switches = build_switch_descriptors(
        cover_id="cover.rollladen_wohnzimmer",
        auto_enabled_entity_id="input_boolean.asc_auto_enabled",
        party_mode_entity_id="input_boolean.asc_party_mode",
    )

    assert {item["name"] for item in switches} == {
        "auto_enabled",
        "party_mode",
    }
    assert all(item["cover_id"] == "cover.rollladen_wohnzimmer" for item in switches)
    assert all(item["enabled"] is True for item in switches)
