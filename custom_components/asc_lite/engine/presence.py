"""Presence-gating decisions for the ASC Lite rule engine."""

from __future__ import annotations

from typing import Any

from .state import StateSnapshot
from .types import Decision

PRESENCE_AWAY_FORCED_OPEN_RULE_ID = "R-PRES-002"
PRESENCE_AWAY_FORCED_OPEN_REASON = "PRESENCE_AWAY_FORCED_OPEN"


def evaluate_presence_rule(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    presence_entity_id: str,
    away_values: set[str] | tuple[str, ...] | None = None,
    open_position: int | float = 100,
    forced_open_cover_ids: set[str] | None = None,
) -> Decision | None:
    """Return a presence decision for forced open when away (kids only).

    Presence now gates only the astro morning open rule via blockers.
    This function returns a forced-open decision for configured child covers
    when presence transitions to away.
    """
    raw_value = snapshot.get(presence_entity_id)
    if raw_value is None:
        return None

    normalized = _normalize_state(raw_value)
    away = {"away", "off", "absent"} if away_values is None else {str(value).lower() for value in away_values}

    if normalized in away:
        if forced_open_cover_ids is not None and cover_id in forced_open_cover_ids:
            return Decision(
                rule_id=PRESENCE_AWAY_FORCED_OPEN_RULE_ID,
                reason_code=PRESENCE_AWAY_FORCED_OPEN_REASON,
                target_position=int(open_position),
            )

    return None


def _normalize_state(value: Any) -> str:
    """Normalize yes/no style state values to a lowercase string."""
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value).strip().lower()


def _mode_matches(mode_values: set[str] | tuple[str, ...], raw_value: Any) -> bool:
    """Check whether a mode string matches the configured open mode set."""
    return _normalize_state(raw_value) in {str(value).lower() for value in mode_values}
