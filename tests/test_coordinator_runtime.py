"""Runtime coordinator tests for B-019 HA wiring."""

from __future__ import annotations

from dataclasses import dataclass

from custom_components.asc_lite.coordinator import (
    ASCLiteCoordinator,
    _is_forced_open_cover,
    _is_terrace_cover,
)
from custom_components.asc_lite.models import (
    CoverConfig,
    GlobalConfig,
    ShadingConfig,
    ThresholdConfig,
)


@dataclass
class FakeState:
    state: str
    attributes: dict


class FakeStates:
    def __init__(self, mapping: dict[str, FakeState]) -> None:
        self._mapping = mapping

    def get(self, entity_id: str):
        return self._mapping.get(entity_id)


class FakeServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def async_call(self, domain: str, service: str, data: dict, blocking: bool = False):
        self.calls.append((domain, service, data))


class FakeHass:
    def __init__(self, state_map: dict[str, FakeState]) -> None:
        self.states = FakeStates(state_map)
        self.services = FakeServices()

    def async_create_task(self, coro):
        # In tests we don't need an active loop for task scheduling assertions.
        return coro


@dataclass
class FakeEntry:
    entry_id: str


def _cover(entity_id: str, name: str) -> CoverConfig:
    return CoverConfig(
        entity_id=entity_id,
        name=name,
        scale=100,
        shading=ShadingConfig(
            azimuth_min=90,
            azimuth_max=180,
            elevation_min=0,
            elevation_max=65,
            thresholds=ThresholdConfig(
                min_temp_c=18,
                lux_enter=400,
                lux_exit=300,
                hysteresis_enabled=True,
            ),
        ),
    )


def _config() -> GlobalConfig:
    return GlobalConfig(
        name="ASC Lite",
        sun_entity_id="sun.sun",
        presence_entity_id="input_boolean.asc_presence_dummy",
        auto_enabled_entity_id="input_boolean.asc_auto_enabled",
        party_mode_entity_id="input_boolean.asc_party_mode",
        terrace_window_entity_id="binary_sensor.terrace_window",
        outdoor_temp_entity_id="sensor.outdoor_temp",
        lux_wz_entity_id="sensor.lux_wz",
        lux_ez_entity_id="sensor.lux_ez",
        invert_positions_global=False,
        manual_block_seconds=3600,
        covers=(
            _cover("cover.rollladen_terrasse", "Terrasse"),
            _cover("cover.rollladen_wohnzimmer", "Wohnzimmer"),
            _cover("cover.rollladen_amelie_fenster", "Amelie Fenster"),
        ),
    )


def test_cover_classification_helpers_match_contract() -> None:
    assert _is_terrace_cover("cover.rollladen_terrasse", "Terrasse") is True
    assert _is_terrace_cover("cover.rollladen_wohnzimmer", "Wohnzimmer") is False
    assert _is_forced_open_cover("cover.rollladen_amelie_fenster") is True
    assert _is_forced_open_cover("cover.rollladen_wohnzimmer") is False


def test_auto_disabled_sets_suppressed_runtime_decision(asyncio_run) -> None:
    coordinator = ASCLiteCoordinator(
        hass=FakeHass(
            {
                "input_boolean.asc_auto_enabled": FakeState("off", {}),
                "input_boolean.asc_presence_dummy": FakeState("on", {}),
                "input_boolean.asc_party_mode": FakeState("off", {}),
                "sun.sun": FakeState("above_horizon", {"elevation": 10, "azimuth": 150}),
                "cover.rollladen_terrasse": FakeState("open", {"current_position": 100}),
                "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 100}),
                "cover.rollladen_amelie_fenster": FakeState("open", {"current_position": 100}),
            }
        ),
        entry=FakeEntry("entry-1"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )

    asyncio_run(coordinator.async_evaluate_once(trigger="unit"))

    assert coordinator.last_decisions["cover.rollladen_terrasse"].reason_code == "AUTO_DISABLED"
    assert coordinator.last_decisions["cover.rollladen_wohnzimmer"].result == "suppressed"


def test_presence_away_forced_open_produces_executed_decision(asyncio_run) -> None:
    coordinator = ASCLiteCoordinator(
        hass=FakeHass(
            {
                "input_boolean.asc_auto_enabled": FakeState("on", {}),
                "input_boolean.asc_presence_dummy": FakeState("away", {}),
                "input_boolean.asc_party_mode": FakeState("off", {}),
                "binary_sensor.terrace_window": FakeState("off", {}),
                "sensor.outdoor_temp": FakeState("22", {}),
                "sensor.lux_wz": FakeState("1200", {}),
                "sensor.lux_ez": FakeState("1000", {}),
                "sun.sun": FakeState("above_horizon", {"elevation": 10, "azimuth": 150}),
                "cover.rollladen_terrasse": FakeState("open", {"current_position": 100}),
                "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 100}),
                "cover.rollladen_amelie_fenster": FakeState("open", {"current_position": 10}),
            }
        ),
        entry=FakeEntry("entry-2"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )

    asyncio_run(coordinator.async_evaluate_once(trigger="unit"))

    result = coordinator.last_decisions["cover.rollladen_amelie_fenster"]
    assert result.rule_id == "R-PRES-002"
    assert result.result == "executed"


def test_coordinator_notifies_registered_listeners(asyncio_run) -> None:
    coordinator = ASCLiteCoordinator(
        hass=FakeHass(
            {
                "input_boolean.asc_auto_enabled": FakeState("off", {}),
                "input_boolean.asc_presence_dummy": FakeState("on", {}),
                "input_boolean.asc_party_mode": FakeState("off", {}),
                "sun.sun": FakeState("above_horizon", {"elevation": 12, "azimuth": 150}),
                "cover.rollladen_terrasse": FakeState("open", {"current_position": 100}),
                "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 100}),
                "cover.rollladen_amelie_fenster": FakeState("open", {"current_position": 100}),
            }
        ),
        entry=FakeEntry("entry-3"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )

    notifications = {"count": 0}

    def _listener() -> None:
        notifications["count"] += 1

    unsub = coordinator.add_listener(_listener)
    asyncio_run(coordinator.async_evaluate_once(trigger="listener_test"))
    unsub()

    assert notifications["count"] == 1
