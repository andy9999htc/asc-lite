"""Standalone local test script for ASC-lite config and position conversion.

This script allows testing without Home Assistant by reading config inputs from
environment variables.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from typing import Any

from custom_components.asc_lite.engine.astro import evaluate_astro_rule
from custom_components.asc_lite.engine.dispatch import DispatchTracker, dispatch_cover_position
from custom_components.asc_lite.engine.manual import ManualBlockManager
from custom_components.asc_lite.engine.party import evaluate_party_rule
from custom_components.asc_lite.engine.position import (
    denormalize_pct_to_native,
    normalize_native_to_pct,
)
from custom_components.asc_lite.engine.presence import evaluate_presence_rule
from custom_components.asc_lite.engine.priority import Decision, PriorityRule, evaluate_rules
from custom_components.asc_lite.engine.shading import evaluate_lux_shading
from custom_components.asc_lite.engine.state import build_state_snapshot
from custom_components.asc_lite.engine.window import evaluate_window_protection
from custom_components.asc_lite.logging import log_decision
from custom_components.asc_lite.coordinator import ASCLiteCoordinator
from custom_components.asc_lite.models import ConfigValidationError, build_runtime_config
from custom_components.asc_lite.sensor import build_diagnostic_sensor_values
from custom_components.asc_lite.switch import build_switch_descriptors


@dataclass
class FakeEntry:
    data: dict[str, Any]
    options: dict[str, Any]
    title: str


@dataclass
class FakeState:
    state: str
    attributes: dict[str, Any]


class FakeStates:
    def __init__(self, mapping: dict[str, FakeState]) -> None:
        self._mapping = mapping

    def get(self, entity_id: str) -> FakeState | None:
        return self._mapping.get(entity_id)


class FakeServices:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def async_call(
        self,
        domain: str,
        service: str,
        data: dict[str, Any],
        blocking: bool = False,
    ) -> None:
        _ = blocking
        self.calls.append((domain, service, data))


class FakeRuntimeHass:
    def __init__(self, state_map: dict[str, FakeState]) -> None:
        self.states = FakeStates(state_map)
        self.services = FakeServices()

    def async_create_task(self, coro: Any) -> Any:
        return asyncio.create_task(coro)


@dataclass
class FakeConfigEntry:
    entry_id: str


def _parse_bool(name: str, default: bool) -> bool:
    """Parse boolean-like environment variables used by this script."""
    raw = os.getenv(name)
    if raw is None:
        return default

    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"{name} must be a boolean-like value")


def _parse_int(name: str, default: int) -> int:
    """Parse integer environment variables with default fallback."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


def _parse_optional_float(name: str) -> float | None:
    """Parse optional float environment variables."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return float(raw)


def _parse_json_env(name: str, default: Any) -> Any:
    """Parse JSON payload from environment variables."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return json.loads(raw)


def build_entry_from_env() -> FakeEntry:
    """Build a fake config entry from environment variables."""
    covers = _parse_json_env(
        "ASC_COVERS_JSON",
        [
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
    )

    data: dict[str, Any] = {
        "name": os.getenv("ASC_NAME", "ASC Lite Standalone"),
        "sun_entity_id": os.getenv("ASC_SUN_ENTITY_ID", "sun.sun"),
        "presence_entity_id": os.getenv(
            "ASC_PRESENCE_ENTITY_ID", "binary_sensor.resident_home"
        ),
        "auto_enabled_entity_id": os.getenv(
            "ASC_AUTO_ENABLED_ENTITY_ID", "input_boolean.asc_auto_enabled"
        ),
        "party_mode_entity_id": os.getenv(
            "ASC_PARTY_MODE_ENTITY_ID", "input_boolean.asc_party_mode"
        ),
        "terrace_window_entity_id": os.getenv("ASC_TERRACE_WINDOW_ENTITY_ID", ""),
        "outdoor_temp_entity_id": os.getenv("ASC_OUTDOOR_TEMP_ENTITY_ID", ""),
        "lux_wz_entity_id": os.getenv("ASC_LUX_WZ_ENTITY_ID", ""),
        "lux_ez_entity_id": os.getenv("ASC_LUX_EZ_ENTITY_ID", ""),
        "invert_positions_global": _parse_bool("ASC_INVERT_POSITIONS_GLOBAL", False),
        "manual_block_seconds": _parse_int("ASC_MANUAL_BLOCK_SECONDS", 3600),
        "covers": covers,
    }

    return FakeEntry(data=data, options={}, title=data["name"])


def run_position_samples(cfg: Any) -> None:
    """Run sample conversions for every configured cover."""
    native_sample_default = _parse_optional_float("ASC_NATIVE_SAMPLE")

    print("\nPosition conversion check:")
    for cover in cfg.covers:
        native = (
            native_sample_default
            if native_sample_default is not None
            else min(cover.scale, 7)
        )

        normalized = normalize_native_to_pct(
            native_position=native,
            scale=cover.scale,
            invert=cfg.invert_positions_global,
        )
        roundtrip = denormalize_pct_to_native(
            percent_position=normalized,
            scale=cover.scale,
            invert=cfg.invert_positions_global,
        )

        print(
            f"- {cover.name} ({cover.entity_id}, scale={cover.scale}): "
            f"native={native} -> pct={normalized} -> native={roundtrip}"
        )


def run_engine_samples(cfg: Any) -> None:
    """Run a small M1 dry-run to exercise priority and snapshot logic."""
    snapshot = build_state_snapshot(
        {
            cfg.sun_entity_id: "night",
            cfg.presence_entity_id: "home",
            cfg.terrace_window_entity_id or "binary_sensor.terrace_window": False,
            cfg.covers[0].entity_id: 0,
        },
        defaults={
            cfg.terrace_window_entity_id or "binary_sensor.terrace_window": False,
            cfg.covers[0].entity_id: 0,
        },
    )

    rules = [
        PriorityRule(
            rule_id="R-LOW",
            priority=10,
            reason_code="LOW",
            predicate=lambda current: current.get(cfg.sun_entity_id) == "night",
            action=lambda current: Decision(
                rule_id="R-LOW",
                reason_code="LOW",
                target_position=0,
            ),
        ),
        PriorityRule(
            rule_id="R-HIGH",
            priority=50,
            reason_code="HIGH",
            predicate=lambda current: current.get(cfg.presence_entity_id) == "home",
            action=lambda current: Decision(
                rule_id="R-HIGH",
                reason_code="HIGH",
                target_position=80,
            ),
        ),
    ]

    decision = evaluate_rules(snapshot, rules)
    print("\nEngine priority dry-run:")
    print(f"- snapshot keys: {sorted(snapshot.values)}")
    print(f"- selected rule: {decision.rule_id if decision else 'none'}")
    print(f"- reason: {decision.reason_code if decision else 'none'}")
    print(f"- target position: {decision.target_position if decision else 'none'}")


def run_m2_samples(cfg: Any) -> None:
    """Run M2 dispatch and manual-block dry-run checks."""
    tracker = DispatchTracker()
    dispatch_cover_position(
        cfg.covers[0].entity_id,
        55,
        tracker=tracker,
        now=100.0,
        command_fn=lambda entity_id, target: print(
            f"- dispatch: {entity_id} -> {target} @ {100.0}"
        ),
    )
    duplicate = dispatch_cover_position(
        cfg.covers[0].entity_id,
        55,
        tracker=tracker,
        now=110.0,
        command_fn=lambda entity_id, target: print(
            f"- dispatch: {entity_id} -> {target} @ {110.0}"
        ),
    )

    manager = ManualBlockManager()
    manager.mark_manual_move(cfg.covers[0].entity_id, now=200.0, duration_seconds=600)

    print("\nM2 dispatch/manual dry-run:")
    print(f"- duplicate suppressed: {duplicate.executed is False} ({duplicate.reason})")
    print(
        "- manual block suppresses shading: "
        f"{manager.should_suppress_auto_action(cfg.covers[0].entity_id, 'shading', now=250.0)}"
    )
    print(
        "- manual block allows evening_down: "
        f"{manager.should_suppress_auto_action(cfg.covers[0].entity_id, 'evening_down', now=250.0)}"
    )


def run_m3_window_sample(cfg: Any) -> None:
    """Run the M3 terrace safety rule dry-runs."""
    terrace_cover_id = cfg.covers[0].entity_id
    terrace_window_id = cfg.terrace_window_entity_id or "binary_sensor.terrace_window"
    snapshot = build_state_snapshot({terrace_window_id: True}, defaults={terrace_window_id: False})

    decision = evaluate_window_protection(
        terrace_cover_id,
        snapshot,
        terrace_window_entity_id=terrace_window_id,
        ventilate_position=35,
        terrace_cover_ids={terrace_cover_id},
    )

    print("\nM3 window-protection dry-run:")
    print(f"- terrace window open: {snapshot.get(terrace_window_id)}")
    print(f"- selected rule: {decision.rule_id if decision else 'none'}")
    print(f"- target position: {decision.target_position if decision else 'none'}")

    party_snapshot = build_state_snapshot(
        {"input_boolean.asc_party_mode": True, terrace_cover_id: 80},
        defaults={"input_boolean.asc_party_mode": False, terrace_cover_id: 0},
    )
    party_decision = evaluate_party_rule(
        terrace_cover_id,
        party_snapshot,
        party_mode_entity_id="input_boolean.asc_party_mode",
        terrace_cover_ids={terrace_cover_id},
    )
    print("\nM3 party-rule dry-run:")
    print(f"- party mode active: {party_snapshot.get('input_boolean.asc_party_mode')}")
    print(f"- selected rule: {party_decision.rule_id if party_decision else 'none'}")
    print(f"- target position: {party_decision.target_position if party_decision else 'none'}")


def run_m3_astro_presence_lux_sample(cfg: Any) -> None:
    """Run the remaining M3 rule dry-runs for astro, presence, and lux."""
    cover_id = cfg.covers[0].entity_id
    sun_entity_id = cfg.sun_entity_id
    presence_entity_id = cfg.presence_entity_id
    lux_entity_id = cfg.lux_wz_entity_id or "sensor.lux_wz"
    temp_entity_id = cfg.outdoor_temp_entity_id or "sensor.outdoor_temp"
    logger = logging.getLogger("custom_components.asc_lite.standalone")

    astro_snapshot = build_state_snapshot(
        {sun_entity_id: {"elevation": -7.0}},
        defaults={sun_entity_id: {"elevation": 0.0}},
    )
    astro_decision = evaluate_astro_rule(
        cover_id,
        astro_snapshot,
        sun_entity_id=sun_entity_id,
        close_elevation=-6,
        close_position=0,
        valid_cover_ids={cover_id},
    )
    print("\nM3 astro dry-run:")
    print(f"- sun elevation: {astro_snapshot.get(sun_entity_id)['elevation']}")
    print(f"- selected rule: {astro_decision.rule_id if astro_decision else 'none'}")
    print(f"- target position: {astro_decision.target_position if astro_decision else 'none'}")
    log_decision(logger, cover_id, "sun_elevation", astro_decision, result="selected")

    presence_snapshot = build_state_snapshot(
        {presence_entity_id: "away"},
        defaults={presence_entity_id: "home"},
    )
    presence_decision = evaluate_presence_rule(
        cover_id,
        presence_snapshot,
        presence_entity_id=presence_entity_id,
        home_values={"home", "on", "present"},
        away_values={"away", "off", "absent"},
        open_position=100,
        close_position=0,
        forced_open_cover_ids={cover_id},
    )
    print("\nM3 presence dry-run:")
    print(f"- presence state: {presence_snapshot.get(presence_entity_id)}")
    print(f"- selected rule: {presence_decision.rule_id if presence_decision else 'none'}")
    print(f"- target position: {presence_decision.target_position if presence_decision else 'none'}")
    log_decision(logger, cover_id, "presence_state", presence_decision, result="selected")

    lux_snapshot = build_state_snapshot(
        {
            lux_entity_id: 1200,
            sun_entity_id: {"azimuth": 140, "elevation": 28},
            temp_entity_id: 22,
        },
        defaults={lux_entity_id: 0, sun_entity_id: {"azimuth": 0, "elevation": 0}, temp_entity_id: 0},
    )
    lux_decision = evaluate_lux_shading(
        cover_id,
        lux_snapshot,
        lux_entity_id=lux_entity_id,
        sun_entity_id=sun_entity_id,
        temp_entity_id=temp_entity_id,
        azimuth_min=90,
        azimuth_max=180,
        elevation_min=0,
        elevation_max=65,
        min_temp_c=18,
        enter_lux=400,
        exit_lux=300,
        shading_position=35,
        restore_position=80,
        non_terrace_cover_ids={cover_id},
        current_position=0,
    )
    print("\nM3 lux-shading dry-run:")
    print(f"- lux value: {lux_snapshot.get(lux_entity_id)}")
    print(f"- selected rule: {lux_decision.rule_id if lux_decision else 'none'}")
    print(f"- target position: {lux_decision.target_position if lux_decision else 'none'}")
    log_decision(logger, cover_id, "lux_shading", lux_decision, result="selected")


def run_m5_runtime_wiring_sample(cfg: Any) -> None:
    """Run a runtime-loop dry-run with the real coordinator and fake HA state."""
    logger = logging.getLogger("custom_components.asc_lite.runtime_standalone")

    state_map: dict[str, FakeState] = {
        cfg.auto_enabled_entity_id: FakeState("on", {}),
        cfg.presence_entity_id: FakeState("away", {}),
        cfg.party_mode_entity_id: FakeState("off", {}),
        cfg.sun_entity_id: FakeState("above_horizon", {"elevation": -7.0, "azimuth": 140.0}),
    }

    if cfg.terrace_window_entity_id:
        state_map[cfg.terrace_window_entity_id] = FakeState("off", {})
    if cfg.outdoor_temp_entity_id:
        state_map[cfg.outdoor_temp_entity_id] = FakeState("22", {})
    if cfg.lux_wz_entity_id:
        state_map[cfg.lux_wz_entity_id] = FakeState("1200", {})
    if cfg.lux_ez_entity_id:
        state_map[cfg.lux_ez_entity_id] = FakeState("900", {})

    for cover in cfg.covers:
        state_map[cover.entity_id] = FakeState("open", {"current_position": 100})

    hass = FakeRuntimeHass(state_map)
    coordinator = ASCLiteCoordinator(
        hass=hass,
        entry=FakeConfigEntry(entry_id="standalone"),
        config=cfg,
        logger=logger,
    )

    async def _run() -> None:
        await coordinator.async_evaluate_once(trigger="standalone_first")
        await asyncio.sleep(0)
        await coordinator.async_evaluate_once(trigger="standalone_second")
        await asyncio.sleep(0)

    asyncio.run(_run())

    print("\nM5 runtime-wiring dry-run (coordinator):")
    for cover in cfg.covers:
        runtime_state = coordinator.last_decisions.get(cover.entity_id)
        if runtime_state is None:
            print(f"- {cover.entity_id}: no runtime decision")
            continue
        print(
            f"- {cover.entity_id}: rule={runtime_state.rule_id} "
            f"reason={runtime_state.reason_code} result={runtime_state.result}"
        )

    print(f"- service calls captured: {len(hass.services.calls)}")
    for domain, service, payload in hass.services.calls:
        print(f"  - {domain}.{service}: {payload}")


def run_m5_diagnostics_projection_sample(cfg: Any) -> None:
    """Project B-020 diagnostic entity payloads from current runtime assumptions."""
    print("\nM5 diagnostics-entity projection dry-run:")

    for cover in cfg.covers:
        sensor_values = build_diagnostic_sensor_values(
            cover_id=cover.entity_id,
            last_decision_rule="R-PRES-001",
            last_decision_reason="PRESENCE_AWAY_CLOSE",
            manual_block_active=False,
        )
        print(
            f"- {cover.entity_id}: "
            f"rule={sensor_values['last_decision_rule']} "
            f"reason={sensor_values['last_decision_reason']} "
            f"manual_block_active={sensor_values['manual_block_active']}"
        )

    first_cover = cfg.covers[0].entity_id
    switch_descriptors = build_switch_descriptors(
        cover_id=first_cover,
        auto_enabled_entity_id=cfg.auto_enabled_entity_id,
        party_mode_entity_id=cfg.party_mode_entity_id,
    )
    print(f"- helper switch descriptors for {first_cover}:")
    for descriptor in switch_descriptors:
        print(
            f"  - name={descriptor['name']} "
            f"entity_id={descriptor['entity_id']} "
            f"enabled={descriptor['enabled']}"
        )


def main() -> int:
    """Run standalone validation and sample position conversion checks."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        entry = build_entry_from_env()
        cfg = build_runtime_config(entry)
    except (ValueError, TypeError, json.JSONDecodeError, ConfigValidationError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print("ASC-lite standalone config validation successful.")
    print(f"Name: {cfg.name}")
    print(f"Covers: {len(cfg.covers)}")
    print(f"Invert global: {cfg.invert_positions_global}")
    print(f"Manual block seconds: {cfg.manual_block_seconds}")

    run_position_samples(cfg)
    run_engine_samples(cfg)
    run_m2_samples(cfg)
    run_m3_window_sample(cfg)
    run_m3_astro_presence_lux_sample(cfg)
    run_m5_runtime_wiring_sample(cfg)
    run_m5_diagnostics_projection_sample(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
