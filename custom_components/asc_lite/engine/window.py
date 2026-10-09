"""Terrace window protection rule for ASC Lite.

When the configured terrace window is open, the terrace cover is forced into a
ventilation target instead of continuing with the normal shading or comfort
logic. Closing the window removes the rule and normal processing can resume.
"""

from __future__ import annotations

from .state import StateSnapshot
from .types import Decision

WINDOW_RULE_ID = "R-WIN-001"
WINDOW_REASON_CODE = "WINDOW_OPEN"


def evaluate_window_protection(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    terrace_window_entity_id: str,
    ventilate_position: int = 35,
    terrace_cover_ids: set[str] | None = None,
) -> Decision | None:
    """Return a ventilation decision when the terrace window is open.

    The rule is intentionally scoped to the configured terrace cover set so other
    shutters remain unaffected by a single terrace window signal.
    """
    if terrace_cover_ids is not None and cover_id not in terrace_cover_ids:
        return None

    value = snapshot.get(terrace_window_entity_id)
    if not _is_truthy(value):
        return None

    return Decision(
        rule_id=WINDOW_RULE_ID,
        reason_code=WINDOW_REASON_CODE,
        target_position=int(ventilate_position),
    )


def _is_truthy(value: object) -> bool:
    """Normalize boolean-like state values used by Home Assistant entities."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        return lowered in {"1", "true", "on", "open", "yes"}
    return bool(value)
