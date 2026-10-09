"""Decision logging helpers for ASC Lite."""

from __future__ import annotations

import logging
from typing import Any

from .engine.types import Decision


def log_decision(
    logger: logging.Logger,
    cover_id: str,
    trigger: str,
    decision: Decision | None,
    *,
    result: str = "selected",
    metadata: dict[str, Any] | None = None,
) -> Decision | None:
    """Log a single ASC Lite decision with the required evidence fields.

    The log message always includes the active shutter, trigger, rule ID,
    outcome, reason code, and target position, so rule-level evidence can be
    reviewed in local logs and during pilot testing.
    """
    if decision is None:
        logger.info(
            "ASC Lite decision: shutter=%s trigger=%s rule_id=%s result=%s reason_code=%s target_position=%s metadata=%s",
            cover_id,
            trigger,
            "none",
            result,
            "none",
            None,
            metadata or {},
        )
        return None

    payload = metadata.copy() if metadata else {}
    payload.update(
        {
            "shutter": cover_id,
            "trigger": trigger,
            "rule_id": decision.rule_id,
            "result": result,
            "reason_code": decision.reason_code,
            "target_position": decision.target_position,
        }
    )

    logger.info(
        "ASC Lite decision: shutter=%s trigger=%s rule_id=%s result=%s reason_code=%s target_position=%s metadata=%s",
        cover_id,
        trigger,
        decision.rule_id,
        result,
        decision.reason_code,
        decision.target_position,
        payload,
    )
    return decision
