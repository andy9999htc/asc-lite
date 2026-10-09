"""Lux shading decisions for non-terrace shutters in the ASC Lite engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .state import StateSnapshot
from .types import Decision

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
        return None

    lux_value = _read_float(snapshot, lux_entity_id)
    if lux_value is None:
        return None

    sun_context = snapshot.get(sun_entity_id)
    azimuth = _read_numeric_from_mapping(sun_context, "azimuth")
    elevation = _read_numeric_from_mapping(sun_context, "elevation")
    if azimuth is not None and not (azimuth_min <= azimuth <= azimuth_max):
        return None
    if elevation is not None and not (elevation_min <= elevation <= elevation_max):
        return None

    if temp_entity_id is not None:
        temp_value = _read_float(snapshot, temp_entity_id)
        if temp_value is not None and temp_value < min_temp_c:
            return None

    if lux_value >= enter_lux:
        return Decision(
            rule_id=LUX_SHADING_IN_RULE_ID,
            reason_code=LUX_SHADING_IN_REASON,
            target_position=int(shading_position),
        )

    if current_position is not None and current_position <= int(shading_position) and lux_value <= exit_lux:
        restore = restore_position if restore_position is not None else open_position
        return Decision(
            rule_id=LUX_SHADING_OUT_RULE_ID,
            reason_code=LUX_SHADING_OUT_REASON,
            target_position=int(restore),
        )

    return None


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
        return _to_float(value.get(key))
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
