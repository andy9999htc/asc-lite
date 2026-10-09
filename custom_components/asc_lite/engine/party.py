"""Party rule for the terrace evening-close behavior in ASC Lite.

The rule is intentionally narrow: party mode suppresses only the terrace
closing action for the configured terrace cover. It does not affect other
shutters or other action classes.
"""

from __future__ import annotations

from .state import StateSnapshot
from .types import Decision

PARTY_RULE_ID = "R-PARTY-001"
PARTY_REASON_CODE = "PARTY_MODE"


def evaluate_party_rule(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    party_mode_entity_id: str,
    terrace_cover_ids: set[str] | None = None,
) -> Decision | None:
    """Return a no-op party-block decision when the terrace should remain open."""
    if terrace_cover_ids is not None and cover_id not in terrace_cover_ids:
        return None

    party_mode = snapshot.get(party_mode_entity_id)
    if not _is_truthy(party_mode):
        return None

    current_position = snapshot.get(cover_id)
    if current_position is None:
        current_position = 0

    return Decision(
        rule_id=PARTY_RULE_ID,
        reason_code=PARTY_REASON_CODE,
        target_position=int(current_position),
    )


def _is_truthy(value: object) -> bool:
    """Normalize boolean-like state values used by Home Assistant entities."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered in {"1", "true", "on", "open", "yes"}
    return bool(value)
