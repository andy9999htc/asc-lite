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
) -> Decision | None:
    """Return an astro close/open decision based on the sun elevation.

    The rule is intentionally narrow: it only uses the sun elevation and the
    configured cover filter. Time-window checks can be applied by the higher
    level controller before dispatching the matching decision.
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
