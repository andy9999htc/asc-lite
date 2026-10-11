"""Astro-based open/close decisions for the ASC Lite rule engine."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .state import StateSnapshot
from .types import Decision

ASTRO_EVENING_CLOSE_RULE_ID = "R-ASTRO-001"
ASTRO_MORNING_OPEN_RULE_ID = "R-ASTRO-002"
ASTRO_EVENING_CLOSE_REASON = "ASTRO_EVENING_CLOSE"
ASTRO_MORNING_OPEN_REASON = "ASTRO_MORNING_OPEN"


def evaluate_astro_rule(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    sun_entity_id: str,
    close_elevation: float = -6.0,
    open_elevation: float = 0.0,
    close_position: int | float = 0,
    open_position: int | float = 100,
    valid_cover_ids: set[str] | None = None,
    presence_entity_id: str | None = None,
    presence_home_values: set[str] | tuple[str, ...] | None = None,
    presence_blocks_morning_open_for: set[str] | None = None,
) -> Decision | None:
    """Return an astro close/open decision based on the sun elevation.

    For morning open on kids' shutters, presence can block the action.
    When presence=home and cover is a kid's shutter, astro morning open is blocked.
    """
    if valid_cover_ids is not None and cover_id not in valid_cover_ids:
        return None

    elevation = _read_elevation(snapshot, sun_entity_id)
    if elevation is None:
        return None

    if elevation <= close_elevation:
        return Decision(
            rule_id=ASTRO_EVENING_CLOSE_RULE_ID,
            reason_code=ASTRO_EVENING_CLOSE_REASON,
            target_position=int(close_position),
        )

    if elevation >= open_elevation:
        # Check presence blocker for kids' morning open
        if (
            presence_entity_id is not None
            and presence_blocks_morning_open_for is not None
            and cover_id in presence_blocks_morning_open_for
        ):
            if _is_presence_home(snapshot, presence_entity_id, presence_home_values):
                return None

        return Decision(
            rule_id=ASTRO_MORNING_OPEN_RULE_ID,
            reason_code=ASTRO_MORNING_OPEN_REASON,
            target_position=int(open_position),
        )

    return None


def _read_elevation(snapshot: StateSnapshot, sun_entity_id: str) -> float | None:
    """Read an elevation value from a direct float, a dict, or a nested state."""
    value = snapshot.get(sun_entity_id)
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("elevation", "sun_elevation", "altitude"):
            nested = value.get(key)
            if nested is not None:
                return _to_float(nested)
    if isinstance(value, (int, float)):
        return float(value)
    return _to_float(value)


def _is_presence_home(
    snapshot: StateSnapshot,
    presence_entity_id: str,
    home_values: set[str] | tuple[str, ...] | None = None,
) -> bool:
    """Check if presence entity indicates home state."""
    raw_value = snapshot.get(presence_entity_id)
    if raw_value is None:
        return False

    normalized = _normalize_state(raw_value)
    home = {"home", "on", "present"} if home_values is None else {str(value).lower() for value in home_values}
    return normalized in home


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


def _normalize_state(value: Any) -> str:
    """Normalize yes/no style state values to a lowercase string."""
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value).strip().lower()
