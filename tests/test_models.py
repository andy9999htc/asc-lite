"""Unit tests for configuration model validation.

These tests intentionally avoid Home Assistant runtime dependencies by using a
minimal fake entry object.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from custom_components.asc_lite.models import ConfigValidationError, build_runtime_config


@dataclass
class FakeEntry:
    data: dict
    options: dict
    title: str = "ASC Lite"


@pytest.fixture
def valid_entry() -> FakeEntry:
    return FakeEntry(
        data={
            "name": "ASC Lite",
            "sun_entity_id": "sun.sun",
            "presence_entity_id": "binary_sensor.resident_home",
            "auto_enabled_entity_id": "input_boolean.asc_auto_enabled",
            "party_mode_entity_id": "input_boolean.asc_party",
            "terrace_window_entity_id": "binary_sensor.window_terrace",
            "outdoor_temp_entity_id": "sensor.outdoor_temp",
            "lux_wz_entity_id": "sensor.lux_wz",
            "lux_ez_entity_id": "sensor.lux_ez",
            "invert_positions_global": False,
            "manual_block_seconds": 3600,
            "covers": [
                {
                    "cover_entity_id": "cover.rollladen_wohnzimmer",
                    "name": "Wohnzimmer",
                    "scale": 100,
                    "azimuth_min": 120,
                    "azimuth_max": 260,
                    "elevation_min": 10,
                    "elevation_max": 65,
                    "min_temp_c": 18,
                    "lux_enter": 400,
                    "lux_exit": 300,
                    "hysteresis_enabled": True,
                }
            ],
        },
        options={},
    )


def test_build_runtime_config_success(valid_entry: FakeEntry) -> None:
    cfg = build_runtime_config(valid_entry)
    assert cfg.manual_block_seconds == 3600
    assert cfg.invert_positions_global is False
    assert len(cfg.covers) == 1
    assert cfg.covers[0].scale == 100


def test_cover_position_defaults_applied_when_omitted(valid_entry: FakeEntry) -> None:
    cfg = build_runtime_config(valid_entry)
    cover = cfg.covers[0]
    assert cover.close_position == 0
    assert cover.shading_position == 35
    assert cover.ventilate_position == 35


def test_cover_position_overrides_applied_from_config(valid_entry: FakeEntry) -> None:
    valid_entry.data["covers"][0]["close_position"] = 15
    valid_entry.data["covers"][0]["shading_position"] = 42
    valid_entry.data["covers"][0]["ventilate_position"] = 28

    cfg = build_runtime_config(valid_entry)
    cover = cfg.covers[0]
    assert cover.close_position == 15
    assert cover.shading_position == 42
    assert cover.ventilate_position == 28


def test_missing_required_binding_rejected(valid_entry: FakeEntry) -> None:
    del valid_entry.data["sun_entity_id"]
    with pytest.raises(ConfigValidationError):
        build_runtime_config(valid_entry)


def test_invalid_cover_scale_rejected(valid_entry: FakeEntry) -> None:
    valid_entry.data["covers"][0]["scale"] = 42
    with pytest.raises(ConfigValidationError):
        build_runtime_config(valid_entry)


def test_non_boolean_invert_rejected(valid_entry: FakeEntry) -> None:
    valid_entry.data["invert_positions_global"] = "false"
    with pytest.raises(ConfigValidationError):
        build_runtime_config(valid_entry)


def test_hysteresis_constraints_rejected(valid_entry: FakeEntry) -> None:
    valid_entry.data["covers"][0]["hysteresis_enabled"] = True
    valid_entry.data["covers"][0]["lux_enter"] = 300
    valid_entry.data["covers"][0]["lux_exit"] = 400
    with pytest.raises(ConfigValidationError):
        build_runtime_config(valid_entry)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("close_position", -1),
        ("close_position", 101),
        ("shading_position", -1),
        ("shading_position", 101),
        ("ventilate_position", -1),
        ("ventilate_position", 101),
    ],
)
def test_cover_position_range_validation_rejected(
    valid_entry: FakeEntry, field: str, value: int
) -> None:
    valid_entry.data["covers"][0][field] = value
    with pytest.raises(ConfigValidationError):
        build_runtime_config(valid_entry)
