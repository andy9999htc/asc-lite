"""Priority-based rule evaluation for the ASC Lite decision engine.

Rules are ordered by priority first and by registration order second. This
ensures the winner is deterministic for a given snapshot and makes it easy to
build predictable rule precedence tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .state import StateSnapshot
from .types import Decision


@dataclass(frozen=True, slots=True)
class PriorityRule:
    """A single rule candidate evaluated against a state snapshot."""

    rule_id: str
    priority: int
    reason_code: str
    predicate: Callable[[StateSnapshot], bool]
    action: Callable[[StateSnapshot], Decision]
    sequence: int = 0


def evaluate_rules(
    snapshot: StateSnapshot,
    rules: list[PriorityRule],
) -> Decision | None:
    """Return the first matching rule ordered by priority and stability.

    Higher priority wins. Equal priorities are evaluated using the original
    registration order, which keeps the outcome deterministic for a fixed rule
    list.
    """
    for rule in sorted(
        rules,
        key=lambda item: (-int(item.priority), int(item.sequence), item.rule_id),
    ):
        if rule.predicate(snapshot):
            return rule.action(snapshot)
    return None
