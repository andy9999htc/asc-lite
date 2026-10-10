"""Runtime service wiring tests for B-021."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass

from custom_components.asc_lite.const import DOMAIN
from custom_components.asc_lite.coordinator import ASCLiteCoordinator
from custom_components.asc_lite.models import CoverConfig, GlobalConfig, ShadingConfig, ThresholdConfig

integration = importlib.import_module("custom_components.asc_lite")


@dataclass
class FakeState:
    state: str
    attributes: dict


class FakeStates:
    def __init__(self, mapping: dict[str, FakeState]) -> None:
        self._mapping = mapping

    def get(self, entity_id: str):
        return self._mapping.get(entity_id)


class FakeServiceRegistry:
    def __init__(self, states: FakeStates) -> None:
        self._handlers: dict[tuple[str, str], object] = {}
        self.states = states
        self.cover_calls: list[dict] = []

    def async_register(self, domain: str, service: str, handler) -> None:
        self._handlers[(domain, service)] = handler

    def async_remove(self, domain: str, service: str) -> None:
        self._handlers.pop((domain, service), None)

    async def async_call(self, domain: str, service: str, data: dict, blocking: bool = False):
        _ = blocking
        if domain == "homeassistant" and service in {"turn_on", "turn_off"}:
            entity_id = data["entity_id"]
            state = self.states.get(entity_id)
            if state is not None:
                state.state = "on" if service == "turn_on" else "off"
            return
        if domain == "cover" and service == "set_cover_position":
            self.cover_calls.append(dict(data))
            return

        handler = self._handlers.get((domain, service))
        if handler is None:
            raise AssertionError(f"Service not registered: {domain}.{service}")

        call = type("Call", (), {"data": data})
        await handler(call)

    def has(self, domain: str, service: str) -> bool:
        return (domain, service) in self._handlers


class FakeHass:
    def __init__(self, state_map: dict[str, FakeState]) -> None:
        self.states = FakeStates(state_map)
        self.services = FakeServiceRegistry(self.states)
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
        covers=(_cover("cover.rollladen_wohnzimmer", "Wohnzimmer"),),
    )


def _build_hass() -> FakeHass:
    return FakeHass(
        {
            "input_boolean.asc_auto_enabled": FakeState("on", {}),
            "input_boolean.asc_presence_dummy": FakeState("off", {}),
            "input_boolean.asc_party_mode": FakeState("off", {}),
            "binary_sensor.terrace_window": FakeState("off", {}),
            "sensor.outdoor_temp": FakeState("22", {}),
            "sensor.lux_wz": FakeState("900", {}),
            "sensor.lux_ez": FakeState("800", {}),
            "sun.sun": FakeState("above_horizon", {"elevation": 20, "azimuth": 140}),
            "cover.rollladen_wohnzimmer": FakeState("open", {"current_position": 50}),
        }
    )


def _install_runtime(hass: FakeHass) -> ASCLiteCoordinator:
    coordinator = ASCLiteCoordinator(
        hass=hass,
        entry=FakeEntry("entry-1"),
        config=_config(),
        logger=__import__("logging").getLogger("asc_lite.test"),
    )
    hass.data[DOMAIN]["entry-1"] = {
        "entry": coordinator.entry,
        "config": coordinator.config,
        "coordinator": coordinator,
    }
    return coordinator


def test_runtime_services_register_and_unregister(asyncio_run) -> None:
    hass = _build_hass()
    _install_runtime(hass)

    asyncio_run(integration._async_register_services(hass))
    assert hass.services.has(DOMAIN, "set_party_mode")
    assert hass.services.has(DOMAIN, "set_auto_enabled")
    assert hass.services.has(DOMAIN, "set_manual_block")
    assert hass.services.has(DOMAIN, "clear_manual_block")

    integration._async_unregister_services(hass)
    assert hass.services.has(DOMAIN, "set_party_mode") is False


def test_set_party_mode_service_toggles_helper(asyncio_run) -> None:
    hass = _build_hass()
    _install_runtime(hass)
    asyncio_run(integration._async_register_services(hass))

    asyncio_run(hass.services.async_call(DOMAIN, "set_party_mode", {"enabled": True}, blocking=True))

    assert hass.states.get("input_boolean.asc_party_mode").state == "on"


def test_set_manual_block_service_affects_runtime_diagnostics(asyncio_run) -> None:
    hass = _build_hass()
    coordinator = _install_runtime(hass)
    asyncio_run(integration._async_register_services(hass))

    asyncio_run(
        hass.services.async_call(
            DOMAIN,
            "set_manual_block",
            {"entity_id": "cover.rollladen_wohnzimmer", "duration": 1200},
            blocking=True,
        )
    )
    hass.states.get("input_boolean.asc_presence_dummy").state = "idle"
    asyncio_run(coordinator.async_evaluate_once(trigger="service_test"))

    state = coordinator.get_cover_runtime_state("cover.rollladen_wohnzimmer")
    assert state.rule_id == "R-ASTRO-002"
    assert state.reason_code == "MANUAL_BLOCK_ACTIVE"
    assert state.result == "suppressed"

    asyncio_run(
        hass.services.async_call(
            DOMAIN,
            "clear_manual_block",
            {"entity_id": "cover.rollladen_wohnzimmer"},
            blocking=True,
        )
    )
    cleared = coordinator.get_cover_runtime_state("cover.rollladen_wohnzimmer")
    assert cleared.reason_code == "MANUAL_BLOCK_CLEARED"
