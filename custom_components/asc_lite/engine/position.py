"""Position normalization helpers for covers with mixed native scales."""

from __future__ import annotations

from ..const import ALLOWED_COVER_SCALES


def normalize_native_to_pct(native_position: float, scale: int, invert: bool = False) -> float:
    """Convert native cover position (0..scale) to normalized percent (0..100)."""
    _validate_scale(scale)
    _validate_range(native_position, 0, scale, "native_position")

    effective_native = (scale - native_position) if invert else native_position
    normalized = (effective_native / scale) * 100
    return round(normalized, 4)


def denormalize_pct_to_native(percent_position: float, scale: int, invert: bool = False) -> int:
    """Convert normalized percent position (0..100) to native cover scale (0..scale)."""
    _validate_scale(scale)
    _validate_range(percent_position, 0, 100, "percent_position")

    effective_native = (percent_position / 100) * scale
    native_value = (scale - effective_native) if invert else effective_native
    return int(round(native_value))


def _validate_scale(scale: int) -> None:
    if scale not in ALLOWED_COVER_SCALES:
        raise ValueError(
            f"Unsupported scale {scale}; allowed scales: {sorted(ALLOWED_COVER_SCALES)}"
        )


def _validate_range(value: float, min_value: float, max_value: float, field_name: str) -> None:
    if value < min_value or value > max_value:
        raise ValueError(f"{field_name} must be in range [{min_value}, {max_value}]")
