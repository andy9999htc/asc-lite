"""Tests for the M2 dispatcher and manual-block logic."""

from __future__ import annotations

from custom_components.asc_lite.engine.dispatch import DispatchTracker, dispatch_cover_position
from custom_components.asc_lite.engine.manual import ManualBlockManager
from custom_components.asc_lite.storage import ManualBlockRecord, restore_manual_block_state


def test_dispatch_deduplicates_same_target_within_30_seconds() -> None:
    calls: list[tuple[str, int]] = []
    tracker = DispatchTracker()

    first = dispatch_cover_position(
        "cover.kitchen",
        55,
        tracker=tracker,
        now=100.0,
        command_fn=lambda entity_id, target: calls.append((entity_id, target)),
    )
    second = dispatch_cover_position(
        "cover.kitchen",
        55,
        tracker=tracker,
        now=120.0,
        command_fn=lambda entity_id, target: calls.append((entity_id, target)),
    )

    assert first.executed is True
    assert first.reason == "executed"
    assert second.executed is False
    assert second.reason == "duplicate"
    assert calls == [("cover.kitchen", 55)]


def test_dispatch_executes_new_target_after_cooldown_or_with_new_position() -> None:
    calls: list[tuple[str, int]] = []
    tracker = DispatchTracker()

    dispatch_cover_position(
        "cover.kitchen",
        40,
        tracker=tracker,
        now=100.0,
        command_fn=lambda entity_id, target: calls.append((entity_id, target)),
    )
    third = dispatch_cover_position(
        "cover.kitchen",
        60,
        tracker=tracker,
        now=130.0,
        command_fn=lambda entity_id, target: calls.append((entity_id, target)),
    )
    fourth = dispatch_cover_position(
        "cover.kitchen",
        60,
        tracker=tracker,
        now=150.0,
        command_fn=lambda entity_id, target: calls.append((entity_id, target)),
    )

    assert third.executed is True
    assert fourth.executed is False
    assert calls == [("cover.kitchen", 40), ("cover.kitchen", 60)]


def test_manual_block_suppresses_shading_and_comfort_only() -> None:
    manager = ManualBlockManager()
    manager.mark_manual_move("cover.kitchen", now=200.0, duration_seconds=600)

    assert manager.should_suppress_auto_action("cover.kitchen", "shading", now=250.0) is True
    assert manager.should_suppress_auto_action("cover.kitchen", "comfort", now=250.0) is True
    assert manager.should_suppress_auto_action("cover.kitchen", "evening_down", now=250.0) is False
    assert manager.should_suppress_auto_action("cover.kitchen", "safety", now=250.0) is False


def test_manual_block_restores_expired_state() -> None:
    record = ManualBlockRecord(cover_id="cover.kitchen", expires_at=300.0, active=True)
    restored = restore_manual_block_state({"cover.kitchen": record}, now=350.0)

    assert restored["cover.kitchen"].active is False
    assert restored["cover.kitchen"].expires_at == 300.0
