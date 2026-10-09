"""Engine helpers for ASC Lite decision-making and state evaluation.

This package keeps the core decision pipeline independent from the Home
Assistant runtime so the unit-tested logic can be exercised in local validation
scripts and pytest runs.
"""

from .dispatch import DispatchResult, DispatchTracker, dispatch_cover_position
from .manual import ManualBlockManager
from .priority import Decision, PriorityRule, evaluate_rules
from .state import StateSnapshot, build_state_snapshot

__all__ = [
    "Decision",
    "DispatchResult",
    "DispatchTracker",
    "ManualBlockManager",
    "PriorityRule",
    "StateSnapshot",
    "build_state_snapshot",
    "dispatch_cover_position",
    "evaluate_rules",
]
