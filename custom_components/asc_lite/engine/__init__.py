"""Engine helpers for ASC Lite decision-making and state evaluation.

This package keeps the core decision pipeline independent from the Home
Assistant runtime so the unit-tested logic can be exercised in local validation
scripts and pytest runs.
"""

from .astro import evaluate_astro_rule
from .dispatch import DispatchResult, DispatchTracker, dispatch_cover_position
from .manual import ManualBlockManager
from .party import evaluate_party_rule
from .presence import evaluate_presence_rule
from .priority import Decision, PriorityRule, evaluate_rules
from .shading import evaluate_lux_shading, evaluate_lux_shading_rule
from .state import StateSnapshot, build_state_snapshot
from .window import evaluate_window_protection

__all__ = [
    "Decision",
    "DispatchResult",
    "DispatchTracker",
    "ManualBlockManager",
    "PriorityRule",
    "StateSnapshot",
    "build_state_snapshot",
    "dispatch_cover_position",
    "evaluate_astro_rule",
    "evaluate_lux_shading",
    "evaluate_lux_shading_rule",
    "evaluate_party_rule",
    "evaluate_presence_rule",
    "evaluate_rules",
    "evaluate_window_protection",
]
