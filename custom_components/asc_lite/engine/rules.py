"""Rule helper definitions used by the ASC Lite MVP logic.

The helpers in this module are intentionally small and dependency-free so they
can be tested in isolation and combined by the future rule engine.
"""

from __future__ import annotations

WINDOW_PROTECTION_RULE_ID = "R-WIN-001"
WINDOW_RESUME_RULE_ID = "R-WIN-002"

__all__ = [
    "WINDOW_PROTECTION_RULE_ID",
    "WINDOW_RESUME_RULE_ID",
]
