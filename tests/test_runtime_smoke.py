"""Runtime smoke checks for HA wiring visibility and first live evaluation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from custom_components.asc_lite.const import DOMAIN
from custom_components.asc_lite.coordinator import ASCLiteCoordinator
from custom_components.asc_lite.models import CoverConfig, GlobalConfig, ShadingConfig, ThresholdConfig
from custom_components.asc_lite import sensor as sensor_platform
from custom_components.asc_lite import switch as switch_platform


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
    async def async_call(self, domain: str, service: str, data: dict, blocking: bool = False):
        _ = (domain, service, data, blocking)


class FakeHass:
    def __init__(self, state_map: dict[str, FakeState]) -> None:
        self.states = FakeStates(state_map)
        self.services = FakeServices()
        self.data: dict = {DOMAIN: {}}

    def async_create_task(self, coro):
        return asyncio.create_task(coro)


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
            _cover("cover.rollladen_wohnzimmer", "Wohnzimmer"),
            _cover("cover.rollladen_terrasse", "Terrasse"),
        ),
    )


def _build_hass() -> FakeHass:
    return FakeHass(
        {
            "input_boolean.asc_auto_enabled": FakeState("on", {}),
            "input_boolean.asc_presence_dummy": FakeState("away", {}),
            "input_boolean.asc_party_mode": FakeState("off", {}),
            "binary_sensor.terrace_window": FakeState("off", {}),
            "sensor.outdoor_temp": FakeState("22", {}),
            "sensor.lux_wz": FakeState("1000", {}),
            "sensor.lux_ez": FakeState("900", {}),
            "sun.sun": FakeState("above_horizon", {"elevation": 12, "azimuth": 140}),
            "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 100}),
            "cover.rollladen_terrasse": FakeState("open", {"current_position": 100}),
        }
    )


def _install_runtime(hass: FakeHass) -> tuple[FakeEntry, ASCLiteCoordinator]:
    entry = FakeEntry(entry_id="entry-smoke")
    coordinator = ASCLiteCoordinator(
        hass=hass,
        entry=entry,
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "config": coordinator.config,
        "coordinator": coordinator,
    }
    return entry, coordinator


def test_runtime_platform_setup_creates_expected_entities(asyncio_run) -> None:
    hass = _build_hass()
    entry, _coordinator = _install_runtime(hass)

    sensors = []
    switches = []

    asyncio_run(sensor_platform.async_setup_entry(hass, entry, lambda entities: sensors.extend(entities)))
    asyncio_run(switch_platform.async_setup_entry(hass, entry, lambda entities: switches.extend(entities)))

    assert len(sensors) == 6
    assert len(switches) == 2


def test_runtime_smoke_first_evaluation_populates_sensor_values(asyncio_run) -> None:
    hass = _build_hass()
    entry, coordinator = _install_runtime(hass)

    sensors = []
    asyncio_run(sensor_platform.async_setup_entry(hass, entry, lambda entities: sensors.extend(entities)))
    asyncio_run(coordinator.async_evaluate_once(trigger="smoke"))

    wohnzimmer_rule_sensor = next(
        sensor
        for sensor in sensors
        if sensor._attr_unique_id.endswith("cover_rollladen_wohnzimmer_last_rule_id")
    )
    wohnzimmer_reason_sensor = next(
        sensor
        for sensor in sensors
        if sensor._attr_unique_id.endswith("cover_rollladen_wohnzimmer_last_reason_code")
    )

    assert wohnzimmer_rule_sensor.native_value == "R-PRES-001"
    assert wohnzimmer_reason_sensor.native_value == "PRESENCE_AWAY_CLOSE"
