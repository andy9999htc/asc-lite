"""Dispatch helpers for ASC Lite cover commands.

This module centralizes the command path and prevents duplicate service calls by
tracking the last target sent for each cover within a 30-second dedupe window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Callable


_DEDUPE_SECONDS = 30.0


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Outcome of a dispatch attempt for one cover."""

    cover_id: str
    target_position: int
    executed: bool
    reason: str
    timestamp: float


@dataclass(slots=True)
class DispatchTracker:
    """Stateful memory for per-cover dedupe history."""

    last_targets: dict[str, tuple[int, float]] = field(default_factory=dict)

    def should_dedupe(self, cover_id: str, target_position: int, now: float) -> bool:
        """Return whether the same target should be suppressed within the dedupe window."""
        previous = self.last_targets.get(cover_id)
        if previous is None:
            return False

        last_target, last_ts = previous
        if last_target != target_position:
            return False

        return (now - last_ts) <= _DEDUPE_SECONDS

    def record(self, cover_id: str, target_position: int, now: float) -> None:
        """Store the last target and timestamp for a cover."""
        self.last_targets[cover_id] = (target_position, now)


def dispatch_cover_position(
    cover_id: str,
    target_position: int,
    *,
    tracker: DispatchTracker | None = None,
    now: float | None = None,
    command_fn: Callable[[str, int], None] | None = None,
) -> DispatchResult:
    """Execute a cover move unless the exact same target is still in dedupe window.

    The default action is a no-op dry-run, which is useful for test and local
    validation scenarios without Home Assistant runtime dependencies.
    """
    current_time = float(monotonic() if now is None else now)
    active_tracker = tracker or DispatchTracker()

    if active_tracker.should_dedupe(cover_id, target_position, current_time):
        return DispatchResult(
            cover_id=cover_id,
            target_position=target_position,
            executed=False,
            reason="duplicate",
            timestamp=current_time,
        )

    if command_fn is not None:
        command_fn(cover_id, target_position)

    active_tracker.record(cover_id, target_position, current_time)
    return DispatchResult(
        cover_id=cover_id,
        target_position=target_position,
        executed=True,
        reason="executed",
        timestamp=current_time,
    )
