"""Lux shading decisions for non-terrace shutters in the ASC Lite engine."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from .state import StateSnapshot
from .types import Decision

_LOGGER = logging.getLogger(__name__)

LUX_SHADING_IN_RULE_ID = "R-LUX-001"
LUX_SHADING_OUT_RULE_ID = "R-LUX-002"
LUX_SHADING_IN_REASON = "LUX_SHADING_IN"
LUX_SHADING_OUT_REASON = "LUX_SHADING_OUT"


def evaluate_lux_shading(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    lux_entity_id: str,
    sun_entity_id: str,
    temp_entity_id: str | None = None,
    min_temp_c: float = 18.0,
    azimuth_min: float = 0.0,
    azimuth_max: float = 360.0,
    elevation_min: float = -90.0,
    elevation_max: float = 90.0,
    enter_lux: float = 400.0,
    exit_lux: float = 300.0,
    shading_position: int | float = 35,
    restore_position: int | float | None = None,
    open_position: int | float = 100,
    non_terrace_cover_ids: set[str] | None = None,
    current_position: int | float | None = None,
) -> Decision | None:
    """Return a lux shading decision for non-terrace shutters.

    The rule is intentionally coarse but matches the MVP decision-table contract:
    it evaluates lux, azimuth/elevation, and optional temperature gating per
    shutter and returns the relevant shade-in or shade-out decision.
    """
    if non_terrace_cover_ids is not None and cover_id not in non_terrace_cover_ids:
        _LOGGER.debug("ASC Lite lux skipped: cover=%s not in non_terrace_cover_ids", cover_id)
        return None

    shading_target = int(shading_position)
    is_currently_shaded = current_position is not None and shading_target -2 <= current_position <= shading_target + 2

    lux_value = _read_float(snapshot, lux_entity_id)
    if lux_value is None:
        _LOGGER.debug("ASC Lite lux skipped: cover=%s lux_entity=%s unavailable", cover_id, lux_entity_id)
        return None

    sun_context = snapshot.get(sun_entity_id)
    azimuth = _read_numeric_from_mapping(sun_context, "azimuth")
    elevation = _read_numeric_from_mapping(sun_context, "elevation")

    if azimuth is not None and not (azimuth_min <= azimuth <= azimuth_max):
        if is_currently_shaded:
            return _build_shading_out_decision(
                cover_id=cover_id,
                current_position=current_position,
                restore_position=restore_position,
                open_position=open_position,
                trigger_message="azimuth=%s outside [%s, %s]",
                trigger_values=(azimuth, azimuth_min, azimuth_max),
            )
        _LOGGER.debug(
            "ASC Lite lux skipped: cover=%s azimuth=%s outside [%s, %s]",
            cover_id,
            azimuth,
            azimuth_min,
            azimuth_max,
        )
        return None
    if elevation is not None and not (elevation_min <= elevation <= elevation_max):
        if is_currently_shaded:
            return _build_shading_out_decision(
                cover_id=cover_id,
                current_position=current_position,
                restore_position=restore_position,
                open_position=open_position,
                trigger_message="elevation=%s outside [%s, %s]",
                trigger_values=(elevation, elevation_min, elevation_max),
            )
        _LOGGER.debug(
            "ASC Lite lux skipped: cover=%s elevation=%s outside [%s, %s]",
            cover_id,
            elevation,
            elevation_min,
            elevation_max,
        )
        return None

    if temp_entity_id is not None:
        temp_value = _read_float(snapshot, temp_entity_id)
        if temp_value is not None and temp_value < min_temp_c:
            if is_currently_shaded:
                return _build_shading_out_decision(
                    cover_id=cover_id,
                    current_position=current_position,
                    restore_position=restore_position,
                    open_position=open_position,
                    trigger_message="temp=%s below min_temp_c=%s",
                    trigger_values=(temp_value, min_temp_c),
                )
            _LOGGER.debug(
                "ASC Lite lux skipped: cover=%s temp=%s below min_temp_c=%s",
                cover_id,
                temp_value,
                min_temp_c,
            )
            return None

    if lux_value >= enter_lux:
        _LOGGER.debug(
            "ASC Lite lux shading in: cover=%s lux=%s enter_lux=%s shading_position=%s",
            cover_id,
            lux_value,
            enter_lux,
            shading_position,
        )
        return Decision(
            rule_id=LUX_SHADING_IN_RULE_ID,
            reason_code=LUX_SHADING_IN_REASON,
            target_position=shading_target,
        )

    if is_currently_shaded and lux_value <= exit_lux:
        return _build_shading_out_decision(
            cover_id=cover_id,
            current_position=current_position,
            restore_position=restore_position,
            open_position=open_position,
            trigger_message="lux=%s exit_lux=%s",
            trigger_values=(lux_value, exit_lux),
        )

    _LOGGER.debug(
        "ASC Lite lux skipped: cover=%s lux=%s enter_lux=%s exit_lux=%s current_position=%s",
        cover_id,
        lux_value,
        enter_lux,
        exit_lux,
        current_position,
    )

    return None


def _build_shading_out_decision(
    *,
    cover_id: str,
    current_position: int | float | None,
    restore_position: int | float | None,
    open_position: int | float,
    trigger_message: str,
    trigger_values: tuple[Any, ...],
) -> Decision:
    """Build a shading-out decision with consistent restore target and logging."""
    restore = restore_position if restore_position is not None else open_position
    _LOGGER.debug(
        "ASC Lite lux shading out: cover=%s " + trigger_message + " current_position=%s restore_position=%s",
        cover_id,
        *trigger_values,
        current_position,
        restore,
    )
    return Decision(
        rule_id=LUX_SHADING_OUT_RULE_ID,
        reason_code=LUX_SHADING_OUT_REASON,
        target_position=int(restore),
    )


def _read_float(snapshot: StateSnapshot, entity_id: str) -> float | None:
    """Read a float from a snapshot entry."""
    value = snapshot.get(entity_id)
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("value", "state", "lux", "reading"):
            nested = value.get(key)
            if nested is not None:
                return _to_float(nested)
    return _to_float(value)


def _read_numeric_from_mapping(value: Any, key: str) -> float | None:
    """Return a numeric field from a dict-like sun-state payload."""
    if value is None:
        return None
    if isinstance(value, Mapping):
        direct_value = _to_float(value.get(key))
        if direct_value is not None:
            return direct_value
        attributes = value.get("attributes")
        if isinstance(attributes, Mapping):
            return _to_float(attributes.get(key))
        return None
    return _to_float(value)


def _to_float(value: Any) -> float | None:
    """Coerce a value to float when it is numeric or string-parsable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def evaluate_lux_shading_rule(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    lux_entity_id: str,
    sun_entity_id: str,
    temp_entity_id: str | None = None,
    min_temp_c: float = 18.0,
    azimuth_min: float = 0.0,
    azimuth_max: float = 360.0,
    elevation_min: float = -90.0,
    elevation_max: float = 90.0,
    enter_lux: float = 400.0,
    exit_lux: float = 300.0,
    shading_position: int | float = 35,
    restore_position: int | float | None = None,
    open_position: int | float = 100,
    non_terrace_cover_ids: set[str] | None = None,
    current_position: int | float | None = None,
) -> Decision | None:
    """Compatibility alias for the lux-shading evaluator."""
    return evaluate_lux_shading(
        cover_id,
        snapshot,
        lux_entity_id=lux_entity_id,
        sun_entity_id=sun_entity_id,
        temp_entity_id=temp_entity_id,
        min_temp_c=min_temp_c,
        azimuth_min=azimuth_min,
        azimuth_max=azimuth_max,
        elevation_min=elevation_min,
        elevation_max=elevation_max,
        enter_lux=enter_lux,
        exit_lux=exit_lux,
        shading_position=shading_position,
        restore_position=restore_position,
        open_position=open_position,
        non_terrace_cover_ids=non_terrace_cover_ids,
        current_position=current_position,
    )
