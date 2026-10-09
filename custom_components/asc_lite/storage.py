"""Storage helpers for persisted manual-block state.

The storage layer is intentionally lightweight and dependency-free so it can be
used both in Home Assistant runtime code and in standalone tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ManualBlockRecord:
    """Persisted manual override state for one shutter."""

    cover_id: str
    expires_at: float
    active: bool
    reason: str = "manual"


def restore_manual_block_state(
    raw_state: Mapping[str, Any] | None,
    *,
    now: float,
) -> dict[str, ManualBlockRecord]:
    """Restore records and drop expired entries.

    This keeps state restoration deterministic and makes it easy to test the
    expiry semantics without a Home Assistant store backend.
    """
    records: dict[str, ManualBlockRecord] = {}
    if not raw_state:
        return records

    for cover_id, value in raw_state.items():
        if not isinstance(value, ManualBlockRecord):
            continue
        if value.active and now >= value.expires_at:
            records[cover_id] = ManualBlockRecord(
                cover_id=cover_id,
                expires_at=value.expires_at,
                active=False,
                reason=value.reason,
            )
        else:
            records[cover_id] = value

    return records
