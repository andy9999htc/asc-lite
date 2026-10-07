"""Config and options flow for ASC Lite.

The flow is intentionally split into two stages:
1) global bindings/settings and
2) per-cover JSON payload.

This keeps the UI compact while still allowing advanced per-cover fields.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import BooleanSelector, NumberSelector, NumberSelectorConfig, TextSelector, TextSelectorConfig

from .const import (
    CONF_AUTO_ENABLED_ENTITY_ID,
    CONF_COVERS,
    CONF_INVERT_POSITIONS_GLOBAL,
    CONF_LUX_EZ_ENTITY_ID,
    CONF_LUX_WZ_ENTITY_ID,
    CONF_MANUAL_BLOCK_SECONDS,
    CONF_NAME,
    CONF_OUTDOOR_TEMP_ENTITY_ID,
    CONF_PARTY_MODE_ENTITY_ID,
    CONF_PRESENCE_ENTITY_ID,
    CONF_SUN_ENTITY_ID,
    CONF_TERRACE_WINDOW_ENTITY_ID,
    DEFAULT_INVERT_POSITIONS_GLOBAL,
    DEFAULT_MANUAL_BLOCK_SECONDS,
    DEFAULT_NAME,
    DEFAULT_SUN_ENTITY_ID,
    DOMAIN,
)
from .models import ConfigValidationError, build_runtime_config

CONF_COVERS_JSON = "covers_json"

REQUIRED_ENTITY_KEYS: tuple[str, ...] = (
    CONF_SUN_ENTITY_ID,
    CONF_PRESENCE_ENTITY_ID,
    CONF_AUTO_ENABLED_ENTITY_ID,
    CONF_PARTY_MODE_ENTITY_ID,
)
OPTIONAL_ENTITY_KEYS: tuple[str, ...] = (
    CONF_TERRACE_WINDOW_ENTITY_ID,
    CONF_OUTDOOR_TEMP_ENTITY_ID,
    CONF_LUX_WZ_ENTITY_ID,
    CONF_LUX_EZ_ENTITY_ID,
)


class ASCLiteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle initial setup for ASC Lite."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ASCLiteOptionsFlow:
        """Return the options flow handler for an existing entry."""
        return ASCLiteOptionsFlow(config_entry)

    _global_data: dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Collect and validate global settings.

        Only required/optional entity references are checked here. Per-cover
        payload validation runs in the next step.
        """
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await _validate_global_entities(self.hass, user_input)
            if not errors:
                self._global_data = user_input
                return await self.async_step_covers()

        return self.async_show_form(
            step_id="user",
            data_schema=_global_schema(user_input),
            errors=errors,
        )

    async def async_step_covers(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Collect per-cover JSON, then run full configuration validation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            covers_json_raw = user_input[CONF_COVERS_JSON]
            covers_list = _parse_covers_json(covers_json_raw)
            if covers_list is None:
                errors["base"] = "invalid_covers_json"
            else:
                merged = {**self._global_data, CONF_COVERS: covers_list}
                errors = await _validate_full_config(self.hass, merged)
                if not errors:
                    return self.async_create_entry(
                        title=str(self._global_data.get(CONF_NAME) or DEFAULT_NAME),
                        data=merged,
                    )

        return self.async_show_form(
            step_id="covers",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_COVERS_JSON,
                        default=_default_covers_json(),
                    ): TextSelector(
                        TextSelectorConfig(multiline=True)
                    )
                }
            ),
            errors=errors,
        )


class ASCLiteOptionsFlow(config_entries.OptionsFlow):
    """Handle post-setup edits for ASC Lite."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Update entry options with the same validation semantics as setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            covers_json_raw = user_input.pop(CONF_COVERS_JSON)
            covers_list = _parse_covers_json(covers_json_raw)
            if covers_list is None:
                errors["base"] = "invalid_covers_json"
            else:
                merged = {**user_input, CONF_COVERS: covers_list}
                errors = await _validate_full_config(self.hass, merged)
                if not errors:
                    return self.async_create_entry(title="", data=merged)

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self._entry, user_input),
            errors=errors,
        )


def _global_schema(user_input: Mapping[str, Any] | None) -> vol.Schema:
    """Build schema for the global setup form step."""
    values = dict(user_input or {})
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=values.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(
                CONF_SUN_ENTITY_ID,
                default=values.get(CONF_SUN_ENTITY_ID, DEFAULT_SUN_ENTITY_ID),
            ): str,
            vol.Required(
                CONF_PRESENCE_ENTITY_ID,
                default=values.get(CONF_PRESENCE_ENTITY_ID, ""),
            ): str,
            vol.Required(
                CONF_AUTO_ENABLED_ENTITY_ID,
                default=values.get(CONF_AUTO_ENABLED_ENTITY_ID, ""),
            ): str,
            vol.Required(
                CONF_PARTY_MODE_ENTITY_ID,
                default=values.get(CONF_PARTY_MODE_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_TERRACE_WINDOW_ENTITY_ID,
                default=values.get(CONF_TERRACE_WINDOW_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_OUTDOOR_TEMP_ENTITY_ID,
                default=values.get(CONF_OUTDOOR_TEMP_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_LUX_WZ_ENTITY_ID,
                default=values.get(CONF_LUX_WZ_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_LUX_EZ_ENTITY_ID,
                default=values.get(CONF_LUX_EZ_ENTITY_ID, ""),
            ): str,
            vol.Required(
                CONF_INVERT_POSITIONS_GLOBAL,
                default=values.get(
                    CONF_INVERT_POSITIONS_GLOBAL, DEFAULT_INVERT_POSITIONS_GLOBAL
                ),
            ): BooleanSelector(),
            vol.Required(
                CONF_MANUAL_BLOCK_SECONDS,
                default=values.get(
                    CONF_MANUAL_BLOCK_SECONDS, DEFAULT_MANUAL_BLOCK_SECONDS
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=60,
                    max=86400,
                    step=60,
                    mode="box",
                )
            ),
        }
    )


def _options_schema(
    entry: config_entries.ConfigEntry,
    user_input: Mapping[str, Any] | None,
) -> vol.Schema:
    """Build schema for the options dialog.

    Existing entry values are used as defaults and overlaid with in-form values
    during validation retries.
    """
    values = _entry_merged(entry)
    if user_input:
        values.update(user_input)

    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=values.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(
                CONF_SUN_ENTITY_ID,
                default=values.get(CONF_SUN_ENTITY_ID, DEFAULT_SUN_ENTITY_ID),
            ): str,
            vol.Required(
                CONF_PRESENCE_ENTITY_ID,
                default=values.get(CONF_PRESENCE_ENTITY_ID, ""),
            ): str,
            vol.Required(
                CONF_AUTO_ENABLED_ENTITY_ID,
                default=values.get(CONF_AUTO_ENABLED_ENTITY_ID, ""),
            ): str,
            vol.Required(
                CONF_PARTY_MODE_ENTITY_ID,
                default=values.get(CONF_PARTY_MODE_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_TERRACE_WINDOW_ENTITY_ID,
                default=values.get(CONF_TERRACE_WINDOW_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_OUTDOOR_TEMP_ENTITY_ID,
                default=values.get(CONF_OUTDOOR_TEMP_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_LUX_WZ_ENTITY_ID,
                default=values.get(CONF_LUX_WZ_ENTITY_ID, ""),
            ): str,
            vol.Optional(
                CONF_LUX_EZ_ENTITY_ID,
                default=values.get(CONF_LUX_EZ_ENTITY_ID, ""),
            ): str,
            vol.Required(
                CONF_INVERT_POSITIONS_GLOBAL,
                default=values.get(
                    CONF_INVERT_POSITIONS_GLOBAL, DEFAULT_INVERT_POSITIONS_GLOBAL
                ),
            ): BooleanSelector(),
            vol.Required(
                CONF_MANUAL_BLOCK_SECONDS,
                default=values.get(
                    CONF_MANUAL_BLOCK_SECONDS, DEFAULT_MANUAL_BLOCK_SECONDS
                ),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=60,
                    max=86400,
                    step=60,
                    mode="box",
                )
            ),
            vol.Required(
                CONF_COVERS_JSON,
                default=json.dumps(values.get(CONF_COVERS, []), indent=2),
            ): TextSelector(TextSelectorConfig(multiline=True)),
        }
    )


async def _validate_global_entities(
    hass: HomeAssistant,
    data: Mapping[str, Any],
) -> dict[str, str]:
    """Validate existence of required and optional global entity bindings."""
    errors: dict[str, str] = {}

    for key in REQUIRED_ENTITY_KEYS:
        value = str(data.get(key, "")).strip()
        if not value or not _entity_exists(hass, value):
            errors["base"] = "entity_not_found"
            return errors

    for key in OPTIONAL_ENTITY_KEYS:
        value = str(data.get(key, "")).strip()
        if value and not _entity_exists(hass, value):
            errors["base"] = "entity_not_found"
            return errors

    return errors


async def _validate_full_config(
    hass: HomeAssistant,
    candidate: dict[str, Any],
) -> dict[str, str]:
    """Validate full candidate config including cover JSON semantics.

    Validation order:
    1) global entity existence,
    2) cover entity existence,
    3) typed model constraints via ``build_runtime_config``.
    """
    errors = await _validate_global_entities(hass, candidate)
    if errors:
        return errors

    for cover in candidate.get(CONF_COVERS, []):
        cover_entity_id = str(cover.get("cover_entity_id", "")).strip()
        if not cover_entity_id or not _entity_exists(hass, cover_entity_id):
            return {"base": "entity_not_found"}

    fake_entry = _EphemeralConfigEntry(candidate)
    try:
        build_runtime_config(fake_entry)
    except ConfigValidationError:
        return {"base": "invalid_cover_settings"}

    return {}


def _entity_exists(hass: HomeAssistant, entity_id: str) -> bool:
    """Check entity existence via registry first, then state machine fallback."""
    registry = er.async_get(hass)
    if registry.async_get(entity_id):
        return True
    return hass.states.get(entity_id) is not None


def _default_covers_json() -> str:
    """Return a starter JSON snippet shown in the config flow text area."""
    return json.dumps(
        [
            {
                "cover_entity_id": "cover.example_living_room",
                "name": "Living Room",
                "scale": 100,
                "azimuth_min": 120,
                "azimuth_max": 260,
                "elevation_min": 10,
                "elevation_max": 65,
                "min_temp_c": 18,
                "lux_enter": 400,
                "lux_exit": 300,
                "hysteresis_enabled": True,
            }
        ],
        indent=2,
    )


def _parse_covers_json(raw: str) -> list[dict[str, Any]] | None:
    """Parse and shape-check the per-cover JSON payload from the form."""
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(decoded, list):
        return None

    if not all(isinstance(item, dict) for item in decoded):
        return None

    return decoded


def _entry_merged(entry: config_entries.ConfigEntry) -> dict[str, Any]:
    """Return effective config values with options overriding original data."""
    return {**entry.data, **entry.options}


class _EphemeralConfigEntry:
    """Minimal object implementing entry.data/options/title for validation."""

    def __init__(self, merged: dict[str, Any]) -> None:
        self.data = merged
        self.options: dict[str, Any] = {}
        self.title = str(merged.get(CONF_NAME, DEFAULT_NAME))
