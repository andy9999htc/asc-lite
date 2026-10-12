"""Astro-based open/close decisions for the ASC Lite rule engine."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from .state import StateSnapshot
from .types import Decision

_LOGGER = logging.getLogger(__name__)

ASTRO_EVENING_CLOSE_RULE_ID = "R-ASTRO-001"
ASTRO_MORNING_OPEN_RULE_ID = "R-ASTRO-002"
ASTRO_EVENING_CLOSE_REASON = "ASTRO_EVENING_CLOSE"
ASTRO_MORNING_OPEN_REASON = "ASTRO_MORNING_OPEN"
_MORNING_OPEN_POSITION_TOLERANCE = 2.0
_DEFAULT_MORNING_OPEN_GRACE_MINUTES = 10
_DEFAULT_EVENING_CLOSE_GRACE_MINUTES = 10


def evaluate_astro_rule(
    cover_id: str,
    snapshot: StateSnapshot,
    *,
    sun_entity_id: str,
    close_elevation: float = -6.0,
    open_elevation: float = 0.0,
    close_position: int | float = 0,
    open_position: int | float = 100,
    current_position: int | float | None = None,
    valid_cover_ids: set[str] | None = None,
    presence_entity_id: str | None = None,
    presence_home_values: set[str] | tuple[str, ...] | None = None,
    presence_blocks_morning_open_for: set[str] | None = None,
    current_datetime: datetime | None = None,
    morning_open_grace_minutes: int = _DEFAULT_MORNING_OPEN_GRACE_MINUTES,
    evening_close_grace_minutes: int = _DEFAULT_EVENING_CLOSE_GRACE_MINUTES,
) -> Decision | None:
    """Return an astro close/open decision based on the sun elevation.

    For morning open on kids' shutters, presence can block the action.
    When presence=home and cover is a kid's shutter, astro morning open is blocked.
    """
    if valid_cover_ids is not None and cover_id not in valid_cover_ids:
        _LOGGER.debug("ASC Lite astro skipped: cover=%s not in valid_cover_ids", cover_id)
        return None

    elevation = _read_elevation(snapshot, sun_entity_id)
    if elevation is None:
        _LOGGER.debug("ASC Lite astro skipped: cover=%s sun=%s elevation unavailable", cover_id, sun_entity_id)
        return None

    if elevation <= close_elevation:
        if not _is_within_evening_window(
            snapshot,
            sun_entity_id,
            current_datetime=current_datetime,
            evening_close_grace_minutes=evening_close_grace_minutes,
        ):
            _LOGGER.debug(
                "ASC Lite astro evening close skipped: cover=%s current_datetime=%s grace_minutes=%s reason=outside_evening_window",
                cover_id,
                current_datetime,
                evening_close_grace_minutes,
            )
            return None

        if current_position is not None:
            distance_to_close = abs(float(current_position) - float(close_position))
            if distance_to_close <= _MORNING_OPEN_POSITION_TOLERANCE:
                _LOGGER.debug(
                    "ASC Lite astro evening close skipped: cover=%s elevation=%s current_position=%s close_position=%s distance_to_close=%s tolerance=%s",
                    cover_id,
                    elevation,
                    current_position,
                    close_position,
                    round(distance_to_close, 3),
                    _MORNING_OPEN_POSITION_TOLERANCE,
                )
                return None

        _LOGGER.debug(
            "ASC Lite astro evening close: cover=%s elevation=%s close_elevation=%s close_position=%s",
            cover_id,
            elevation,
            close_elevation,
            close_position,
        )
        return Decision(
            rule_id=ASTRO_EVENING_CLOSE_RULE_ID,
            reason_code=ASTRO_EVENING_CLOSE_REASON,
            target_position=int(close_position),
        )

    if elevation >= open_elevation:
        if not _is_within_morning_window(
            snapshot,
            sun_entity_id,
            current_datetime=current_datetime,
            morning_open_grace_minutes=morning_open_grace_minutes,
        ):
            _LOGGER.debug(
                "ASC Lite astro morning open skipped: cover=%s current_datetime=%s grace_minutes=%s reason=outside_morning_window",
                cover_id,
                current_datetime,
                morning_open_grace_minutes,
            )
            return None

        # Morning-open should only trigger when the cover is effectively at the
        # configured close target. Otherwise daytime rules (for example lux
        # shading) can oscillate against astro open.
        if current_position is not None:
            distance_to_close = abs(float(current_position) - float(close_position))
            if distance_to_close > _MORNING_OPEN_POSITION_TOLERANCE:
                _LOGGER.debug(
                    "ASC Lite astro morning open skipped: cover=%s elevation=%s current_position=%s close_position=%s distance_to_close=%s tolerance=%s",
                    cover_id,
                    elevation,
                    current_position,
                    close_position,
                    round(distance_to_close, 3),
                    _MORNING_OPEN_POSITION_TOLERANCE,
                )
                return None

        # Check presence blocker for kids' morning open
        if (
            presence_entity_id is not None
            and presence_blocks_morning_open_for is not None
            and cover_id in presence_blocks_morning_open_for
        ):
            if _is_presence_home(snapshot, presence_entity_id, presence_home_values):
                _LOGGER.debug(
                    "ASC Lite astro morning open blocked by presence: cover=%s presence_entity=%s elevation=%s",
                    cover_id,
                    presence_entity_id,
                    elevation,
                )
                return None

        _LOGGER.debug(
            "ASC Lite astro morning open: cover=%s elevation=%s open_elevation=%s open_position=%s",
            cover_id,
            elevation,
            open_elevation,
            open_position,
        )
        return Decision(
            rule_id=ASTRO_MORNING_OPEN_RULE_ID,
            reason_code=ASTRO_MORNING_OPEN_REASON,
            target_position=int(open_position),
        )

    return None


def _is_within_morning_window(
    snapshot: StateSnapshot,
    sun_entity_id: str,
    *,
    current_datetime: datetime | None,
    morning_open_grace_minutes: int,
) -> bool:
    """Allow morning-open until sunrise (open-elevation crossing) plus grace minutes."""
    if current_datetime is None:
        return True

    if morning_open_grace_minutes < 0:
        morning_open_grace_minutes = 0

    next_rising = _read_next_rising(snapshot, sun_entity_id)
    if next_rising is None:
        # Keep behavior permissive when sunrise timestamp is unavailable.
        return True

    if current_datetime.tzinfo is None and next_rising.tzinfo is not None:
        current_datetime = current_datetime.replace(tzinfo=next_rising.tzinfo)
    if current_datetime.tzinfo is not None and next_rising.tzinfo is None:
        next_rising = next_rising.replace(tzinfo=current_datetime.tzinfo)

    sunrise_anchor = next_rising
    # After sunrise, HA's next_rising usually points to tomorrow.
    # If the next rising is far in the future, anchor to previous day.
    if current_datetime > next_rising or (next_rising - current_datetime) > timedelta(hours=12):
        sunrise_anchor = next_rising - timedelta(days=1)

    cutoff = sunrise_anchor + timedelta(minutes=morning_open_grace_minutes)
    return current_datetime <= cutoff


def _is_within_evening_window(
    snapshot: StateSnapshot,
    sun_entity_id: str,
    *,
    current_datetime: datetime | None,
    evening_close_grace_minutes: int,
) -> bool:
    """Allow evening-close until sunset (close-elevation crossing) plus grace minutes."""
    if current_datetime is None:
        return True

    if evening_close_grace_minutes < 0:
        evening_close_grace_minutes = 0

    next_setting = _read_next_setting(snapshot, sun_entity_id)
    if next_setting is None:
        # Keep behavior permissive when sunset timestamp is unavailable.
        return True

    if current_datetime.tzinfo is None and next_setting.tzinfo is not None:
        current_datetime = current_datetime.replace(tzinfo=next_setting.tzinfo)
    if current_datetime.tzinfo is not None and next_setting.tzinfo is None:
        next_setting = next_setting.replace(tzinfo=current_datetime.tzinfo)

    sunset_anchor = next_setting
    # After sunset, HA's next_setting usually points to tomorrow.
    if current_datetime > next_setting or (next_setting - current_datetime) > timedelta(hours=12):
        sunset_anchor = next_setting - timedelta(days=1)

    cutoff = sunset_anchor + timedelta(minutes=evening_close_grace_minutes)
    return current_datetime <= cutoff


def _read_next_rising(snapshot: StateSnapshot, sun_entity_id: str) -> datetime | None:
    """Read sun next_rising timestamp from snapshot sun payload."""
    value = snapshot.get(sun_entity_id)
    if not isinstance(value, Mapping):
        return None

    raw_next_rising = value.get("next_rising")
    if raw_next_rising is None:
        return None
    if isinstance(raw_next_rising, datetime):
        return raw_next_rising
    if isinstance(raw_next_rising, str):
        candidate = raw_next_rising.strip()
        if not candidate:
            return None
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _read_next_setting(snapshot: StateSnapshot, sun_entity_id: str) -> datetime | None:
    """Read sun next_setting timestamp from snapshot sun payload."""
    value = snapshot.get(sun_entity_id)
    if not isinstance(value, Mapping):
        return None

    raw_next_setting = value.get("next_setting")
    if raw_next_setting is None:
        return None
    if isinstance(raw_next_setting, datetime):
        return raw_next_setting
    if isinstance(raw_next_setting, str):
        candidate = raw_next_setting.strip()
        if not candidate:
            return None
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _read_elevation(snapshot: StateSnapshot, sun_entity_id: str) -> float | None:
    """Read an elevation value from a direct float, a dict, or a nested state."""
    value = snapshot.get(sun_entity_id)
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("elevation", "sun_elevation", "altitude"):
            nested = value.get(key)
            if nested is not None:
                return _to_float(nested)
    if isinstance(value, (int, float)):
        return float(value)
    return _to_float(value)


def _is_presence_home(
    snapshot: StateSnapshot,
    presence_entity_id: str,
    home_values: set[str] | tuple[str, ...] | None = None,
) -> bool:
    """Check if presence entity indicates home state."""
    raw_value = snapshot.get(presence_entity_id)
    if raw_value is None:
        return False

    normalized = _normalize_state(raw_value)
    home = {"home", "on", "present"} if home_values is None else {str(value).lower() for value in home_values}
    return normalized in home


def _to_float(value: Any) -> float | None:
    """Coerce a value to float when it is numeric or string-parsable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _normalize_state(value: Any) -> str:
    """Normalize yes/no style state values to a lowercase string."""
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, bool):
        return "on" if value else "off"
    return str(value).strip().lower()
