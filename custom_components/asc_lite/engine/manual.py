"""Manual-block logic for ASC Lite auto-action suppression.

The rule system may suppress shading/comfort actions during a manual override,
while allowing evening-down and safety/window-triggered action classes to keep
running.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..storage import ManualBlockRecord, restore_manual_block_state

_AUTO_SUPPRESS_ACTIONS = {"shading", "comfort"}
_ALWAYS_ALLOWED_ACTIONS = {"evening_down", "safety", "window"}


@dataclass(slots=True)
class ManualBlockManager:
    """Track manual override blocks per shutter and evaluate action suppression."""

    blocks: dict[str, ManualBlockRecord] = field(default_factory=dict)
    internal_markers: dict[str, float] = field(default_factory=dict)

    def mark_manual_move(
        self,
        cover_id: str,
        *,
        now: float,
        duration_seconds: int = 3600,
    ) -> ManualBlockRecord:
        """Set a manual override block for a cover.

        The block is considered active until the configured timeout expires.
        """
        record = ManualBlockRecord(
            cover_id=cover_id,
            expires_at=now + float(duration_seconds),
            active=True,
            reason="manual",
        )
        self.blocks[cover_id] = record
        return record

    def mark_internal_command(self, cover_id: str, *, now: float, duration_seconds: int = 30) -> float:
        """Mark that the integration itself issued a command for this shutter."""
        expiry = now + float(duration_seconds)
        self.internal_markers[cover_id] = expiry
        return expiry

    def has_internal_command(self, cover_id: str, *, now: float) -> bool:
        """Return whether an internal command marker is still active for this shutter."""
        expiry = self.internal_markers.get(cover_id)
        if expiry is None:
            return False
        if now >= expiry:
            self.internal_markers.pop(cover_id, None)
            return False
        return True

    def is_active(self, cover_id: str, *, now: float) -> bool:
        """Return whether the cover currently has an active manual block."""
        record = self.blocks.get(cover_id)
        if record is None:
            return False
        if now >= record.expires_at:
            self.blocks[cover_id] = ManualBlockRecord(
                cover_id=cover_id,
                expires_at=record.expires_at,
                active=False,
                reason=record.reason,
            )
            return False
        return record.active

    def should_suppress_auto_action(
        self,
        cover_id: str,
        action_type: str,
        *,
        now: float,
    ) -> bool:
        """Whether the provided auto-action class should be withheld by manual block."""
        if action_type in _ALWAYS_ALLOWED_ACTIONS:
            return False
        if action_type not in _AUTO_SUPPRESS_ACTIONS:
            return False
        return self.is_active(cover_id, now=now)

    def restore_from_storage(self, payload: dict[str, Any] | None, *, now: float) -> None:
        """Restore persisted manual-block records and drop expired entries."""
        restored = restore_manual_block_state(payload or {}, now=now)
        self.blocks = dict(restored)

    def clear_expired(self, *, now: float) -> None:
        """Remove expired manual-block entries to keep storage small."""
        for cover_id, record in list(self.blocks.items()):
            if now >= record.expires_at:
                self.blocks.pop(cover_id, None)
