"""Typed runtime models for ASC Lite configuration.

The model layer is intentionally independent from Home Assistant runtime types
so validation can be reused in unit tests and standalone tooling.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Protocol

from .const import (
    ALLOWED_COVER_SCALES,
    CONF_AUTO_ENABLED_ENTITY_ID,
    CONF_AZIMUTH_MAX,
    CONF_AZIMUTH_MIN,
    CONF_CLOSE_POSITION,
    CONF_COVER_ENTITY_ID,
    CONF_COVER_NAME,
    CONF_COVER_SCALE,
    CONF_COVERS,
    CONF_ELEVATION_MAX,
    CONF_ELEVATION_MIN,
    CONF_HYSTERESIS_ENABLED,
    CONF_INVERT_POSITIONS_GLOBAL,
    CONF_LUX_ENTER,
    CONF_LUX_EZ_ENTITY_ID,
    CONF_LUX_EXIT,
    CONF_LUX_WZ_ENTITY_ID,
    CONF_MANUAL_BLOCK_SECONDS,
    CONF_MIN_TEMP_C,
    CONF_MORNING_OPEN_WEEKEND_TIME,
    CONF_NAME,
    CONF_OUTDOOR_TEMP_ENTITY_ID,
    CONF_PARTY_MODE_ENTITY_ID,
    CONF_PRESENCE_MANAGED,
    CONF_PRESENCE_ENTITY_ID,
    CONF_SHADING_POSITION,
    CONF_SUN_ENTITY_ID,
    DEFAULT_CLOSE_POSITION,
    DEFAULT_INVERT_POSITIONS_GLOBAL,
    DEFAULT_MANUAL_BLOCK_SECONDS,
    DEFAULT_SHADING_POSITION,
)


class ConfigValidationError(ValueError):
    """Raised when runtime configuration is invalid."""


class EntryLike(Protocol):
    """Minimal config-entry contract needed by ``build_runtime_config``."""

    data: dict[str, Any]
    options: dict[str, Any]
    title: str


@dataclass(frozen=True, slots=True)
class ThresholdConfig:
    """Thresholds used by shading evaluation."""

    min_temp_c: float | None
    lux_enter: float
    lux_exit: float
    hysteresis_enabled: bool

    def __post_init__(self) -> None:
        if self.lux_enter < 0 or self.lux_exit < 0:
            raise ConfigValidationError("Lux thresholds must be non-negative")
        if self.hysteresis_enabled and self.lux_exit > self.lux_enter:
            raise ConfigValidationError(
                "lux_exit must be <= lux_enter when hysteresis is enabled"
            )


@dataclass(frozen=True, slots=True)
class ShadingConfig:
    """Per-shutter shading constraints."""

    azimuth_min: float
    azimuth_max: float
    elevation_min: float
    elevation_max: float
    thresholds: ThresholdConfig

    def __post_init__(self) -> None:
        if self.azimuth_min > self.azimuth_max:
            raise ConfigValidationError("azimuth_min must be <= azimuth_max")
        if self.elevation_min > self.elevation_max:
            raise ConfigValidationError("elevation_min must be <= elevation_max")


@dataclass(frozen=True, slots=True)
class CoverConfig:
    """Per-cover configuration and references."""

    entity_id: str
    name: str
    scale: int
    shading: ShadingConfig
    close_position: int = DEFAULT_CLOSE_POSITION
    shading_position: int = DEFAULT_SHADING_POSITION
    morning_open_weekend_time: str | None = None
    presence_managed: bool = False

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ConfigValidationError("Cover entity_id is required")
        if self.scale not in ALLOWED_COVER_SCALES:
            raise ConfigValidationError(
                f"Unsupported cover scale {self.scale}; allowed: {sorted(ALLOWED_COVER_SCALES)}"
            )
        _ensure_pct_range(self.close_position, "close_position")
        _ensure_pct_range(self.shading_position, "shading_position")
        _ensure_optional_time_hhmm(self.morning_open_weekend_time, "morning_open_weekend_time")
        if not isinstance(self.presence_managed, bool):
            raise ConfigValidationError("presence_managed must be a boolean")


@dataclass(frozen=True, slots=True)
class GlobalConfig:
    """Global integration configuration for one config entry."""

    name: str
    sun_entity_id: str
    presence_entity_id: str
    auto_enabled_entity_id: str
    party_mode_entity_id: str
    outdoor_temp_entity_id: str | None
    lux_wz_entity_id: str | None
    lux_ez_entity_id: str | None
    invert_positions_global: bool
    manual_block_seconds: int
    covers: tuple[CoverConfig, ...]

    def __post_init__(self) -> None:
        if not self.sun_entity_id:
            raise ConfigValidationError("sun_entity_id is required")
        if not self.presence_entity_id:
            raise ConfigValidationError("presence_entity_id is required")
        if not self.auto_enabled_entity_id:
            raise ConfigValidationError("auto_enabled_entity_id is required")
        if not self.party_mode_entity_id:
            raise ConfigValidationError("party_mode_entity_id is required")
        if self.manual_block_seconds <= 0:
            raise ConfigValidationError("manual_block_seconds must be > 0")
        if not self.covers:
            raise ConfigValidationError("At least one cover must be configured")


def build_runtime_config(entry: EntryLike) -> GlobalConfig:
    """Build and validate runtime config from entry data/options.

    ``entry.options`` overrides ``entry.data`` to match Home Assistant option
    semantics.
    """
    merged: dict[str, Any] = {**entry.data, **entry.options}

    covers_raw = merged.get(CONF_COVERS, [])
    if not isinstance(covers_raw, list):
        raise ConfigValidationError("covers must be a list")

    covers: list[CoverConfig] = []
    for index, item in enumerate(covers_raw):
        if not isinstance(item, dict):
            raise ConfigValidationError(f"covers[{index}] must be an object")

        entity_id = _require_string(item, CONF_COVER_ENTITY_ID, f"covers[{index}]")
        name = str(item.get(CONF_COVER_NAME) or entity_id)
        scale = _require_int(item, CONF_COVER_SCALE, f"covers[{index}]")
        close_position = _optional_int_with_default(
            item,
            CONF_CLOSE_POSITION,
            f"covers[{index}]",
            default=DEFAULT_CLOSE_POSITION,
        )
        shading_position = _optional_int_with_default(
            item,
            CONF_SHADING_POSITION,
            f"covers[{index}]",
            default=DEFAULT_SHADING_POSITION,
        )
        morning_open_weekend_time = _optional_time_hhmm(
            item.get(CONF_MORNING_OPEN_WEEKEND_TIME),
            f"covers[{index}]",
            CONF_MORNING_OPEN_WEEKEND_TIME,
        )
        presence_managed = _optional_bool_with_default(
            item,
            CONF_PRESENCE_MANAGED,
            f"covers[{index}]",
            default=False,
        )
        thresholds = ThresholdConfig(
            min_temp_c=_optional_float(item.get(CONF_MIN_TEMP_C)),
            lux_enter=_require_float(item, CONF_LUX_ENTER, f"covers[{index}]"),
            lux_exit=_require_float(item, CONF_LUX_EXIT, f"covers[{index}]"),
            hysteresis_enabled=bool(item.get(CONF_HYSTERESIS_ENABLED, True)),
        )

        shading = ShadingConfig(
            azimuth_min=_require_float(item, CONF_AZIMUTH_MIN, f"covers[{index}]"),
            azimuth_max=_require_float(item, CONF_AZIMUTH_MAX, f"covers[{index}]"),
            elevation_min=_require_float(item, CONF_ELEVATION_MIN, f"covers[{index}]"),
            elevation_max=_require_float(item, CONF_ELEVATION_MAX, f"covers[{index}]"),
            thresholds=thresholds,
        )

        covers.append(
            CoverConfig(
                entity_id=entity_id,
                name=name,
                scale=scale,
                close_position=close_position,
                shading_position=shading_position,
                morning_open_weekend_time=morning_open_weekend_time,
                presence_managed=presence_managed,
                shading=shading,
            )
        )

    return GlobalConfig(
        name=str(merged.get(CONF_NAME) or entry.title),
        sun_entity_id=_require_string(merged, CONF_SUN_ENTITY_ID, "global"),
        presence_entity_id=_require_string(merged, CONF_PRESENCE_ENTITY_ID, "global"),
        auto_enabled_entity_id=_require_string(
            merged, CONF_AUTO_ENABLED_ENTITY_ID, "global"
        ),
        party_mode_entity_id=_require_string(merged, CONF_PARTY_MODE_ENTITY_ID, "global"),
        outdoor_temp_entity_id=_optional_string(merged.get(CONF_OUTDOOR_TEMP_ENTITY_ID)),
        lux_wz_entity_id=_optional_string(merged.get(CONF_LUX_WZ_ENTITY_ID)),
        lux_ez_entity_id=_optional_string(merged.get(CONF_LUX_EZ_ENTITY_ID)),
        invert_positions_global=_require_bool(
            merged,
            CONF_INVERT_POSITIONS_GLOBAL,
            "global",
            default=DEFAULT_INVERT_POSITIONS_GLOBAL,
        ),
        manual_block_seconds=_require_positive_int(
            merged,
            CONF_MANUAL_BLOCK_SECONDS,
            "global",
            default=DEFAULT_MANUAL_BLOCK_SECONDS,
        ),
        covers=tuple(covers),
    )


def _require_string(data: dict[str, Any], key: str, section: str) -> str:
    """Read required non-empty string field or raise validation error."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{section}.{key} is required")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    """Normalize optional string field to stripped value or None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigValidationError("Optional entity id values must be strings")
    candidate = value.strip()
    return candidate or None


def _require_int(data: dict[str, Any], key: str, section: str) -> int:
    """Read required integer field.

    Bool values are rejected because they are a subclass of int in Python and
    typically indicate invalid UI input.
    """
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigValidationError(f"{section}.{key} must be an integer")
    return value


def _require_positive_int(
    data: dict[str, Any], key: str, section: str, *, default: int | None = None
) -> int:
    """Read positive integer field with optional default fallback."""
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ConfigValidationError(f"{section}.{key} must be an integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, float) and value.is_integer():
        result = int(value)
    else:
        raise ConfigValidationError(f"{section}.{key} must be an integer")

    if result <= 0:
        raise ConfigValidationError(f"{section}.{key} must be > 0")
    return result


def _require_bool(
    data: dict[str, Any], key: str, section: str, *, default: bool | None = None
) -> bool:
    """Read strict boolean field with optional default fallback."""
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{section}.{key} must be a boolean")
    return value


def _require_float(data: dict[str, Any], key: str, section: str) -> float:
    """Read required numeric field as float."""
    value = data.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    raise ConfigValidationError(f"{section}.{key} must be numeric")


def _optional_float(value: Any) -> float | None:
    """Read optional numeric field as float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    raise ConfigValidationError("Optional float value must be numeric")


def _optional_int_with_default(
    data: dict[str, Any], key: str, section: str, *, default: int
) -> int:
    """Read optional integer field with default fallback."""
    value = data.get(key, default)
    if isinstance(value, bool):
        raise ConfigValidationError(f"{section}.{key} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ConfigValidationError(f"{section}.{key} must be an integer")


def _optional_bool_with_default(
    data: dict[str, Any], key: str, section: str, *, default: bool
) -> bool:
    """Read optional bool field with default fallback."""
    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ConfigValidationError(f"{section}.{key} must be a boolean")
    return value


def _ensure_pct_range(value: int, field_name: str) -> None:
    """Ensure per-cover target positions use normalized 0..100 range."""
    if value < 0 or value > 100:
        raise ConfigValidationError(f"{field_name} must be in range [0, 100]")


_HHMM_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _optional_time_hhmm(value: Any, section: str, key: str) -> str | None:
    """Read optional HH:MM time field and normalize it."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ConfigValidationError(f"{section}.{key} must be a string in HH:MM format")

    candidate = value.strip()
    if not candidate:
        return None
    if _HHMM_PATTERN.fullmatch(candidate) is None:
        raise ConfigValidationError(f"{section}.{key} must be in HH:MM format")
    return candidate


def _ensure_optional_time_hhmm(value: str | None, field_name: str) -> None:
    """Validate optional HH:MM values for dataclass-level safety."""
    if value is None:
        return
    if _HHMM_PATTERN.fullmatch(value) is None:
        raise ConfigValidationError(f"{field_name} must be in HH:MM format")
