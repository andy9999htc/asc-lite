"""Shared datatypes for the ASC Lite decision engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Decision:
    """A single decision result selected by a rule evaluation cycle."""

    rule_id: str
    reason_code: str
    target_position: int | float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
