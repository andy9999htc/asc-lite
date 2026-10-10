"""Runtime coordinator for ASC Lite Home Assistant execution.

This module bridges the existing decision engine into Home Assistant runtime.
It runs a periodic evaluation loop, selects decisions per cover, and dispatches
cover commands through the existing dedupe-aware dispatch helper.
"""

from __future__ import annotations

import logging as py_logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
from time import monotonic
from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.event import async_track_time_interval
except ModuleNotFoundError:  # pragma: no cover - enables standalone/local tests
    ConfigEntry = Any  # type: ignore[assignment]
    HomeAssistant = Any  # type: ignore[assignment]

    def async_track_time_interval(*args: Any, **kwargs: Any):  # type: ignore[misc]
        return lambda: None

from .engine.astro import evaluate_astro_rule
from .engine.dispatch import DispatchTracker, dispatch_cover_position
from .engine.manual import ManualBlockManager
from .engine.party import evaluate_party_rule
from .engine.position import denormalize_pct_to_native
from .engine.presence import evaluate_presence_rule
from .engine.shading import evaluate_lux_shading
from .engine.state import StateSnapshot
from .engine.types import Decision
from .engine.window import evaluate_window_protection
from .logging import log_decision
from .models import CoverConfig, GlobalConfig

_UPDATE_INTERVAL = timedelta(seconds=30)
_FORCED_OPEN_SUFFIXES = (
    "amelie_fenster",
    "amelie_tuer",
    "schlafzimmer_fenster",
    "schlafzimmer_tuer",
)
_MANUAL_BLOCK_REASON = "MANUAL_BLOCK_ACTIVE"
_SUPPRESSED_BY_MANUAL_RULES = {
    "R-LUX-001",
    "R-LUX-002",
    "R-ASTRO-002",
    "R-PRES-003",
}


@dataclass(slots=True)
class RuntimeDecisionState:
    """Track last decision evidence for each cover."""

    rule_id: str = "none"
    reason_code: str = "none"
    result: str = "skipped"


@dataclass(slots=True)
class ASCLiteCoordinator:
    """Evaluate ASC-lite rules on a periodic schedule inside Home Assistant."""

    hass: HomeAssistant
    entry: ConfigEntry
    config: GlobalConfig
    logger: py_logging.Logger
    tracker: DispatchTracker = field(default_factory=DispatchTracker)
    manual_blocks: ManualBlockManager = field(default_factory=ManualBlockManager)
    last_decisions: dict[str, RuntimeDecisionState] = field(default_factory=dict)
    _listeners: list[Callable[[], None]] = field(default_factory=list)
    _unsub_interval: Any = None

    async def async_start(self) -> None:
        """Start periodic runtime evaluation for this config entry."""
        await self.async_evaluate_once(trigger="startup")

        async def _async_tick(_now: Any) -> None:
            await self.async_evaluate_once(trigger="interval")

        self._unsub_interval = async_track_time_interval(self.hass, _async_tick, _UPDATE_INTERVAL)

    async def async_stop(self) -> None:
        """Stop periodic runtime evaluation for this config entry."""
        if self._unsub_interval is not None:
            self._unsub_interval()
            self._unsub_interval = None

    def add_listener(self, callback: Any) -> Any:
        """Register a callback invoked after each evaluation cycle."""
        self._listeners.append(callback)

        def _unsubscribe() -> None:
            try:
                self._listeners.remove(callback)
            except ValueError:
                return

        return _unsubscribe

    def get_cover_runtime_state(self, cover_id: str) -> RuntimeDecisionState:
        """Return the last runtime decision state for one cover."""
        return self.last_decisions.get(cover_id, RuntimeDecisionState())

    def contains_cover(self, cover_id: str) -> bool:
        """Return whether this coordinator manages the requested cover."""
        return any(item.entity_id == cover_id for item in self.config.covers)

    async def async_set_party_mode(self, enabled: bool) -> None:
        """Set the configured party-mode helper and trigger immediate re-evaluation."""
        await self._async_set_helper_state(self.config.party_mode_entity_id, enabled)
        await self.async_evaluate_once(trigger="service_set_party_mode")

    async def async_set_auto_enabled(self, enabled: bool) -> None:
        """Set the configured auto-enabled helper and trigger immediate re-evaluation."""
        await self._async_set_helper_state(self.config.auto_enabled_entity_id, enabled)
        await self.async_evaluate_once(trigger="service_set_auto_enabled")

    async def async_set_manual_block(
        self,
        cover_id: str,
        *,
        duration: int | None = None,
        reason: str | None = None,
    ) -> None:
        """Set manual block state for one cover and notify listeners immediately."""
        if not self.contains_cover(cover_id):
            return
        seconds = int(duration or self.config.manual_block_seconds)
        self.manual_blocks.mark_manual_move(
            cover_id,
            now=monotonic(),
            duration_seconds=seconds,
        )
        self.last_decisions[cover_id] = RuntimeDecisionState(
            rule_id="manual_block",
            reason_code=_MANUAL_BLOCK_REASON,
            result="suppressed",
        )
        self.logger.info(
            "ASC Lite manual block set: shutter=%s duration=%s reason=%s",
            cover_id,
            seconds,
            reason or "manual",
        )
        self._notify_listeners()

    async def async_clear_manual_block(self, cover_id: str) -> None:
        """Clear manual block state for one cover and notify listeners."""
        if not self.contains_cover(cover_id):
            return
        self.manual_blocks.blocks.pop(cover_id, None)
        self.last_decisions[cover_id] = RuntimeDecisionState(
            rule_id="manual_block",
            reason_code="MANUAL_BLOCK_CLEARED",
            result="executed",
        )
        self.logger.info("ASC Lite manual block cleared: shutter=%s", cover_id)
        self._notify_listeners()

    async def async_evaluate_once(self, *, trigger: str) -> None:
        """Run one full decision pass for all configured covers."""
        snapshot = self._build_snapshot()

        if not _is_truthy(snapshot.get(self.config.auto_enabled_entity_id, True)):
            for cover in self.config.covers:
                self.last_decisions[cover.entity_id] = RuntimeDecisionState(
                    rule_id="none",
                    reason_code="AUTO_DISABLED",
                    result="suppressed",
                )
                log_decision(
                    self.logger,
                    cover.entity_id,
                    trigger,
                    None,
                    result="auto_disabled",
                    metadata={"reason_code": "AUTO_DISABLED"},
                )
            self._notify_listeners()
            return

        for cover in self.config.covers:
            await self._async_evaluate_cover(snapshot, cover, trigger=trigger)
        self._notify_listeners()

    async def _async_evaluate_cover(
        self,
        snapshot: StateSnapshot,
        cover: CoverConfig,
        *,
        trigger: str,
    ) -> None:
        cover_id = cover.entity_id
        decision = self._evaluate_cover(snapshot, cover)
        if decision is None:
            self.last_decisions[cover_id] = RuntimeDecisionState()
            log_decision(self.logger, cover_id, trigger, None, result="no_match")
            return

        if self._should_suppress_by_manual_block(cover_id, decision):
            self.last_decisions[cover_id] = RuntimeDecisionState(
                rule_id=decision.rule_id,
                reason_code=_MANUAL_BLOCK_REASON,
                result="suppressed",
            )
            log_decision(
                self.logger,
                cover_id,
                trigger,
                decision,
                result="manual_block_active",
                metadata={"reason_code": _MANUAL_BLOCK_REASON},
            )
            return

        native_target = denormalize_pct_to_native(
            float(decision.target_position or 0),
            cover.scale,
            invert=self.config.invert_positions_global,
        )

        result = dispatch_cover_position(
            cover_id,
            native_target,
            tracker=self.tracker,
            command_fn=self._command_cover_position,
        )
        dispatch_state = "executed" if result.executed else "suppressed"
        self.last_decisions[cover_id] = RuntimeDecisionState(
            rule_id=decision.rule_id,
            reason_code=decision.reason_code,
            result=dispatch_state,
        )
        log_decision(
            self.logger,
            cover_id,
            trigger,
            decision,
            result=dispatch_state,
            metadata={"native_target": native_target},
        )

    def _evaluate_cover(self, snapshot: StateSnapshot, cover: CoverConfig) -> Decision | None:
        cover_id = cover.entity_id
        terrace_cover_ids = {
            item.entity_id
            for item in self.config.covers
            if _is_terrace_cover(item.entity_id, item.name)
        }

        if self.config.terrace_window_entity_id:
            window_decision = evaluate_window_protection(
                cover_id,
                snapshot,
                terrace_window_entity_id=self.config.terrace_window_entity_id,
                terrace_cover_ids=terrace_cover_ids,
            )
            if window_decision is not None:
                return window_decision

        party_decision = evaluate_party_rule(
            cover_id,
            snapshot,
            party_mode_entity_id=self.config.party_mode_entity_id,
            terrace_cover_ids=terrace_cover_ids,
        )
        if party_decision is not None:
            return party_decision

        forced_open_ids = {
            item.entity_id
            for item in self.config.covers
            if _is_forced_open_cover(item.entity_id)
        }
        presence_decision = evaluate_presence_rule(
            cover_id,
            snapshot,
            presence_entity_id=self.config.presence_entity_id,
            forced_open_cover_ids=forced_open_ids,
        )
        if presence_decision is not None:
            return presence_decision

        astro_decision = evaluate_astro_rule(
            cover_id,
            snapshot,
            sun_entity_id=self.config.sun_entity_id,
            valid_cover_ids={item.entity_id for item in self.config.covers},
        )
        if astro_decision is not None:
            return astro_decision

        lux_entity_id = _resolve_lux_entity_id(self.config, cover_id)
        if lux_entity_id:
            lux_decision = evaluate_lux_shading(
                cover_id,
                snapshot,
                lux_entity_id=lux_entity_id,
                sun_entity_id=self.config.sun_entity_id,
                temp_entity_id=self.config.outdoor_temp_entity_id,
                min_temp_c=(cover.shading.thresholds.min_temp_c or 18.0),
                azimuth_min=cover.shading.azimuth_min,
                azimuth_max=cover.shading.azimuth_max,
                elevation_min=cover.shading.elevation_min,
                elevation_max=cover.shading.elevation_max,
                enter_lux=cover.shading.thresholds.lux_enter,
                exit_lux=cover.shading.thresholds.lux_exit,
                non_terrace_cover_ids={
                    item.entity_id
                    for item in self.config.covers
                    if not _is_terrace_cover(item.entity_id, item.name)
                },
                current_position=_read_cover_position_pct(snapshot, cover_id),
            )
            if lux_decision is not None:
                return lux_decision

        return None

    def _build_snapshot(self) -> StateSnapshot:
        raw: dict[str, Any] = {}

        for cover in self.config.covers:
            raw[cover.entity_id] = _read_state_value(self.hass, cover.entity_id)

        raw[self.config.sun_entity_id] = _read_state_value(self.hass, self.config.sun_entity_id)
        raw[self.config.presence_entity_id] = _read_state_value(self.hass, self.config.presence_entity_id)
        raw[self.config.auto_enabled_entity_id] = _read_state_value(self.hass, self.config.auto_enabled_entity_id)
        raw[self.config.party_mode_entity_id] = _read_state_value(self.hass, self.config.party_mode_entity_id)

        if self.config.terrace_window_entity_id:
            raw[self.config.terrace_window_entity_id] = _read_state_value(
                self.hass,
                self.config.terrace_window_entity_id,
            )
        if self.config.outdoor_temp_entity_id:
            raw[self.config.outdoor_temp_entity_id] = _read_state_value(
                self.hass,
                self.config.outdoor_temp_entity_id,
            )
        if self.config.lux_wz_entity_id:
            raw[self.config.lux_wz_entity_id] = _read_state_value(self.hass, self.config.lux_wz_entity_id)
        if self.config.lux_ez_entity_id:
            raw[self.config.lux_ez_entity_id] = _read_state_value(self.hass, self.config.lux_ez_entity_id)

        return StateSnapshot(values=raw)

    def _command_cover_position(self, cover_id: str, target_position: int) -> None:
        self.hass.async_create_task(
            self.hass.services.async_call(
                "cover",
                "set_cover_position",
                {"entity_id": cover_id, "position": int(target_position)},
                blocking=False,
            )
        )

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:  # pragma: no cover - defensive guard for HA callbacks
                self.logger.exception("ASC Lite listener callback failed")

    async def _async_set_helper_state(self, helper_entity_id: str, enabled: bool) -> None:
        service = "turn_on" if enabled else "turn_off"
        await self.hass.services.async_call(
            "homeassistant",
            service,
            {"entity_id": helper_entity_id},
            blocking=True,
        )

    def _should_suppress_by_manual_block(self, cover_id: str, decision: Decision) -> bool:
        if decision.rule_id not in _SUPPRESSED_BY_MANUAL_RULES:
            return False
        self.manual_blocks.clear_expired(now=monotonic())
        return self.manual_blocks.is_active(cover_id, now=monotonic())


def _read_state_value(hass: HomeAssistant, entity_id: str) -> Any:
    """Read one entity value from HA state machine with sun/cover conveniences."""
    state = hass.states.get(entity_id)
    if state is None:
        return None

    if entity_id.startswith("sun."):
        return {
            "state": state.state,
            "elevation": state.attributes.get("elevation"),
            "azimuth": state.attributes.get("azimuth"),
        }

    if entity_id.startswith("cover."):
        if "current_position" in state.attributes:
            return state.attributes.get("current_position")
        return state.state

    return state.state


def _read_cover_position_pct(snapshot: StateSnapshot, cover_id: str) -> float | None:
    value = snapshot.get(cover_id)
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    lowered = str(value).strip().lower()
    return lowered in {"1", "true", "on", "open", "yes", "home", "present"}


def _is_terrace_cover(entity_id: str, name: str) -> bool:
    marker = f"{entity_id} {name}".lower()
    return "terrasse" in marker or "terrace" in marker


def _is_forced_open_cover(entity_id: str) -> bool:
    lowered = entity_id.lower()
    return any(lowered.endswith(suffix) for suffix in _FORCED_OPEN_SUFFIXES)


def _resolve_lux_entity_id(config: GlobalConfig, cover_id: str) -> str | None:
    lowered = cover_id.lower()
    if "wohnzimmer" in lowered or "terrasse" in lowered:
        return config.lux_wz_entity_id or config.lux_ez_entity_id
    return config.lux_ez_entity_id or config.lux_wz_entity_id
