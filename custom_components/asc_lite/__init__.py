"""ASC Lite integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, LOGGER_NAME
from .models import build_runtime_config

_LOGGER = logging.getLogger(LOGGER_NAME)

_PLATFORMS: list[str] = []


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up ASC Lite from YAML (not used)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ASC Lite from a config entry."""
    runtime_config = build_runtime_config(entry)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "entry": entry,
        "config": runtime_config,
    }

    if _PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    _LOGGER.debug("ASC Lite entry %s set up", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an ASC Lite config entry."""
    unload_ok = True
    if _PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        _LOGGER.debug("ASC Lite entry %s unloaded", entry.entry_id)

    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
