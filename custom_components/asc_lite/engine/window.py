"""Terrace window protection rule for ASC Lite.

When the configured terrace window is open, the terrace cover is forced into a
ventilation target instead of continuing with the normal shading or comfort
logic. Closing the window removes the rule and normal processing can resume.
"""

from __future__ import annotations

import logging

from .state import StateSnapshot
from .types import Decision

_LOGGER = logging.getLogger(__name__)

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
        _LOGGER.debug("ASC Lite window skipped: cover=%s not in terrace_cover_ids", cover_id)
        return None

    value = snapshot.get(terrace_window_entity_id)
    is_open = _is_truthy(value)
    if _is_contact_sensor(terrace_window_entity_id):
        is_open = not is_open

    if not is_open:
        _LOGGER.debug("ASC Lite window skipped: cover=%s terrace_window=%s", cover_id, value)
        return None

    _LOGGER.debug(
        "ASC Lite window protection: cover=%s terrace_window=%s ventilate_position=%s",
        cover_id,
        value,
        ventilate_position,
    )
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


def _is_contact_sensor(entity_id: str) -> bool:
    """Detect inverted contact sensors by their entity id suffix."""
    return entity_id.lower().rsplit(".", 1)[-1].endswith("_contact")
