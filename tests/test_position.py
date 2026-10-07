"""Unit tests for native<->normalized position conversion helpers."""

from __future__ import annotations

import pytest

from custom_components.asc_lite.engine.position import (
    denormalize_pct_to_native,
    normalize_native_to_pct,
)


def test_normalize_scale_100_no_inversion() -> None:
    assert normalize_native_to_pct(0, 100, invert=False) == 0
    assert normalize_native_to_pct(80, 100, invert=False) == 80
    assert normalize_native_to_pct(100, 100, invert=False) == 100


def test_normalize_scale_10_no_inversion() -> None:
    assert normalize_native_to_pct(0, 10, invert=False) == 0
    assert normalize_native_to_pct(7, 10, invert=False) == 70
    assert normalize_native_to_pct(10, 10, invert=False) == 100


def test_inversion_applied_consistently() -> None:
    assert normalize_native_to_pct(0, 100, invert=True) == 100
    assert normalize_native_to_pct(80, 100, invert=True) == 20

    assert denormalize_pct_to_native(100, 100, invert=True) == 0
    assert denormalize_pct_to_native(20, 100, invert=True) == 80


def test_roundtrip_no_inversion() -> None:
    for native in (0, 10, 35, 60, 80, 100):
        pct = normalize_native_to_pct(native, 100, invert=False)
        assert denormalize_pct_to_native(pct, 100, invert=False) == native


def test_roundtrip_scale_10_with_inversion() -> None:
    for native in (0, 3, 5, 7, 10):
        pct = normalize_native_to_pct(native, 10, invert=True)
        assert denormalize_pct_to_native(pct, 10, invert=True) == native


def test_invalid_scale_raises() -> None:
    with pytest.raises(ValueError):
        normalize_native_to_pct(5, 42)


def test_out_of_range_positions_raise() -> None:
    with pytest.raises(ValueError):
        normalize_native_to_pct(-1, 100)

    with pytest.raises(ValueError):
        normalize_native_to_pct(101, 100)

    with pytest.raises(ValueError):
        denormalize_pct_to_native(-1, 100)

    with pytest.raises(ValueError):
        denormalize_pct_to_native(101, 100)
