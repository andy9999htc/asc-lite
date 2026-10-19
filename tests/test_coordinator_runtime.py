"""Runtime coordinator tests for B-019 HA wiring."""

from __future__ import annotations

from dataclasses import dataclass

from custom_components.asc_lite.coordinator import (
    ASCLiteCoordinator,
    _is_terrace_cover,
)
from custom_components.asc_lite.engine.types import Decision
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


def _cover(
    entity_id: str,
    name: str,
    weekend_time: str | None = None,
    *,
    presence_managed: bool = False,
) -> CoverConfig:
    return CoverConfig(
        entity_id=entity_id,
        name=name,
        scale=100,
        morning_open_weekend_time=weekend_time,
        presence_managed=presence_managed,
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
        outdoor_temp_entity_id="sensor.outdoor_temp",
        lux_wz_entity_id="sensor.lux_wz",
        lux_ez_entity_id="sensor.lux_ez",
        invert_positions_global=False,
        manual_block_seconds=3600,
        covers=(
            _cover("cover.rollladen_terrasse", "Terrasse", "08:00"),
            _cover("cover.rollladen_wohnzimmer", "Wohnzimmer", "08:00"),
            _cover(
                "cover.rollladen_amelie_fenster",
                "Amelie Fenster",
                "09:00",
                presence_managed=True,
            ),
        ),
    )


def test_cover_classification_helpers_match_contract() -> None:
    assert _is_terrace_cover("cover.rollladen_terrasse", "Terrasse") is True
    assert _is_terrace_cover("cover.rollladen_wohnzimmer", "Wohnzimmer") is False


def test_presence_managed_flag_marks_forced_open_covers() -> None:
    config = _config()

    managed = {cover.entity_id for cover in config.covers if cover.presence_managed}

    assert managed == {"cover.rollladen_amelie_fenster"}


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


def test_unavailable_cover_is_skipped_without_dispatch(asyncio_run) -> None:
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
                "cover.rollladen_wohnzimmer": FakeState("unavailable", {}),
                "cover.rollladen_amelie_fenster": FakeState("open", {"current_position": 10}),
            }
        ),
        entry=FakeEntry("entry-4"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )

    asyncio_run(coordinator.async_evaluate_once(trigger="unit"))

    result = coordinator.last_decisions["cover.rollladen_wohnzimmer"]
    assert result.reason_code == "COVER_UNAVAILABLE"
    assert result.result == "suppressed"
    assert all(
        call[2].get("entity_id") != "cover.rollladen_wohnzimmer"
        for call in coordinator.hass.services.calls
    )


def test_astro_rule_runs_only_once_per_day_per_cover(asyncio_run, monkeypatch) -> None:
    def _fake_astro(*args, **kwargs):  # type: ignore[no-untyped-def]
        return Decision(
            rule_id="R-ASTRO-002",
            reason_code="ASTRO_MORNING_OPEN",
            target_position=100,
        )

    monkeypatch.setattr("custom_components.asc_lite.coordinator.evaluate_astro_rule", _fake_astro)

    coordinator = ASCLiteCoordinator(
        hass=FakeHass(
            {
                "input_boolean.asc_auto_enabled": FakeState("on", {}),
                "input_boolean.asc_presence_dummy": FakeState("on", {}),
                "input_boolean.asc_party_mode": FakeState("off", {}),
                "binary_sensor.terrace_window": FakeState("off", {}),
                "sensor.outdoor_temp": FakeState("22", {}),
                "sensor.lux_wz": FakeState("100", {}),
                "sensor.lux_ez": FakeState("100", {}),
                "sun.sun": FakeState(
                    "above_horizon",
                    {
                        "elevation": 10,
                        "azimuth": 150,
                        "next_rising": "2026-10-14T07:44:00+02:00",
                        "next_setting": "2026-10-14T18:36:00+02:00",
                    },
                ),
                "cover.rollladen_terrasse": FakeState("open", {"current_position": 20}),
                "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 20}),
                "cover.rollladen_amelie_fenster": FakeState("open", {"current_position": 20}),
            }
        ),
        entry=FakeEntry("entry-5"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )

    asyncio_run(coordinator.async_evaluate_once(trigger="unit"))
    first_call_count = len(coordinator.hass.services.calls)

    asyncio_run(coordinator.async_evaluate_once(trigger="unit"))
    second_call_count = len(coordinator.hass.services.calls)

    assert first_call_count > 0
    assert second_call_count == first_call_count
    assert coordinator.last_decisions["cover.rollladen_wohnzimmer"].reason_code == "ASTRO_ALREADY_EXECUTED_TODAY"
    assert coordinator.last_decisions["cover.rollladen_wohnzimmer"].result == "suppressed"


def test_coordinator_forwards_weekend_morning_time_per_cover(asyncio_run, monkeypatch) -> None:
    captured: list[tuple[str, str | None]] = []

    def _fake_astro(cover_id, snapshot, **kwargs):  # type: ignore[no-untyped-def]
        _ = snapshot
        captured.append((cover_id, kwargs.get("morning_open_weekend_time")))
        return None

    monkeypatch.setattr("custom_components.asc_lite.coordinator.evaluate_astro_rule", _fake_astro)

    coordinator = ASCLiteCoordinator(
        hass=FakeHass(
            {
                "input_boolean.asc_auto_enabled": FakeState("on", {}),
                "input_boolean.asc_presence_dummy": FakeState("on", {}),
                "input_boolean.asc_party_mode": FakeState("off", {}),
                "sensor.outdoor_temp": FakeState("22", {}),
                "sensor.lux_wz": FakeState("100", {}),
                "sensor.lux_ez": FakeState("100", {}),
                "sun.sun": FakeState(
                    "above_horizon",
                    {
                        "elevation": 10,
                        "azimuth": 150,
                        "next_rising": "2026-10-14T07:44:00+02:00",
                        "next_setting": "2026-10-14T18:36:00+02:00",
                    },
                ),
                "cover.rollladen_terrasse": FakeState("open", {"current_position": 20}),
                "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 20}),
                "cover.rollladen_amelie_fenster": FakeState("open", {"current_position": 20}),
            }
        ),
        entry=FakeEntry("entry-6"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )

    asyncio_run(coordinator.async_evaluate_once(trigger="unit"))

    assert set(captured) == {
        ("cover.rollladen_terrasse", "08:00"),
        ("cover.rollladen_wohnzimmer", "08:00"),
        ("cover.rollladen_amelie_fenster", "09:00"),
    }
