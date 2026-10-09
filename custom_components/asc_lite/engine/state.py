"""Snapshot helpers for current entity states and fallback handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

_UNKNOWN_VALUES = {None, "unknown", "unavailable", "none"}


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    """A normalized view of the state values relevant for a decision pass."""

    values: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Return the stored value or fallback/default if it is stale or unknown."""
        value = self.values.get(key, default)
        if value is None or str(value).lower() in {"unknown", "unavailable", "none"}:
            return default
        return value

    def items(self):
        """Return the underlying entries as a key/value iterator."""
        return self.values.items()

    def __contains__(self, key: str) -> bool:
        return key in self.values


def build_state_snapshot(
    raw_states: Mapping[str, Any] | None = None,
    defaults: Mapping[str, Any] | None = None,
) -> StateSnapshot:
    """Create a snapshot with fallback values for missing or stale entities.

    Any value equivalent to ``None``, ``unknown`` or ``unavailable`` is treated as
    a stale state and replaced with the provided fallback when available.
    """
    merged: dict[str, Any] = {}
    if defaults:
        merged.update(defaults)
    if raw_states:
        for key, value in raw_states.items():
            merged[key] = value

    resolved: dict[str, Any] = {}
    for key, value in merged.items():
        if value is None:
            resolved[key] = defaults.get(key) if defaults and key in defaults else None
            continue
        if isinstance(value, str) and value.strip().lower() in _UNKNOWN_VALUES:
            resolved[key] = defaults.get(key) if defaults and key in defaults else None
            continue
        resolved[key] = value

    return StateSnapshot(values=resolved)
