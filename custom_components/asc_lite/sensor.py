"""Diagnostic sensor helpers for ASC Lite runtime state.

These helpers are intentionally dependency-free so their output can be tested
without a running Home Assistant instance. They provide the human-readable
values expected for rule decisions and manual-block state.
"""

from __future__ import annotations

from typing import Any


def build_diagnostic_sensor_values(
    *,
    cover_id: str,
    last_decision_rule: str | None = None,
    last_decision_reason: str | None = None,
    manual_block_active: bool = False,
) -> dict[str, Any]:
    """Return stable diagnostic values for a shutter.

    The values are designed to be consumed by Home Assistant sensor entities and
    remain easy to inspect in local dry runs.
    """
    return {
        "cover_id": cover_id,
        "last_decision_rule": last_decision_rule or "unknown",
        "last_decision_reason": last_decision_reason or "unknown",
        "manual_block_active": bool(manual_block_active),
    }
