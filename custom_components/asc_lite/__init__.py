"""Home Assistant integration entrypoint for ASC Lite.

The module wires config entries into runtime state and handles reload/unload
lifecycles. Business rules are implemented in dedicated engine modules.
"""

from __future__ import annotations

import logging as py_logging
from typing import Any

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.core import ServiceCall
except ModuleNotFoundError:  # pragma: no cover - enables standalone local tests
    ConfigEntry = Any  # type: ignore[assignment]
    HomeAssistant = Any  # type: ignore[assignment]
    ServiceCall = Any  # type: ignore[assignment]

from .const import DOMAIN, LOGGER_NAME
from .coordinator import ASCLiteCoordinator
from .models import build_runtime_config

_LOGGER = py_logging.getLogger(LOGGER_NAME)

_PLATFORMS: list[str] = ["sensor", "switch"]
_RUNTIME_KEYS = {"_services_registered"}
_SERVICE_SET_MANUAL_BLOCK = "set_manual_block"
_SERVICE_CLEAR_MANUAL_BLOCK = "clear_manual_block"
_SERVICE_SET_PARTY_MODE = "set_party_mode"
_SERVICE_SET_AUTO_ENABLED = "set_auto_enabled"
_REGISTERED_SERVICES = (
    _SERVICE_SET_MANUAL_BLOCK,
    _SERVICE_CLEAR_MANUAL_BLOCK,
    _SERVICE_SET_PARTY_MODE,
    _SERVICE_SET_AUTO_ENABLED,
)


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up ASC Lite from YAML.

    YAML setup is intentionally a no-op for MVP because configuration is handled
    through config entries only.
    """
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ASC Lite from a config entry.

    Runtime config is validated and cached under ``hass.data[DOMAIN]`` so later
    coordinator/engine steps can use a typed, pre-validated model.
    """
    runtime_config = build_runtime_config(entry)
    coordinator = ASCLiteCoordinator(
        hass=hass,
        entry=entry,
        config=runtime_config,
        logger=_LOGGER,
    )
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "entry": entry,
        "config": runtime_config,
        "coordinator": coordinator,
    }

    if _PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    await _async_register_services(hass)
    await coordinator.async_start()

    _LOGGER.debug("ASC Lite entry %s set up", entry.entry_id)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an ASC Lite config entry and remove cached runtime state."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = runtime.get("coordinator")
    if coordinator is not None:
        await coordinator.async_stop()

    unload_ok = True
    if _PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not _iter_coordinators(hass):
            _async_unregister_services(hass)
        _LOGGER.debug("ASC Lite entry %s unloaded", entry.entry_id)

    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options are updated in the UI."""
    await hass.config_entries.async_reload(entry.entry_id)


def _iter_coordinators(hass: HomeAssistant) -> list[ASCLiteCoordinator]:
    runtimes = hass.data.get(DOMAIN, {})
    coordinators: list[ASCLiteCoordinator] = []
    for key, value in runtimes.items():
        if key in _RUNTIME_KEYS:
            continue
        coordinator = value.get("coordinator") if isinstance(value, dict) else None
        if coordinator is not None:
            coordinators.append(coordinator)
    return coordinators


def _match_coordinators_by_cover(hass: HomeAssistant, cover_id: str) -> list[ASCLiteCoordinator]:
    return [coordinator for coordinator in _iter_coordinators(hass) if coordinator.contains_cover(cover_id)]


async def _async_register_services(hass: HomeAssistant) -> None:
    runtimes = hass.data.setdefault(DOMAIN, {})
    if runtimes.get("_services_registered"):
        return

    async def _handle_set_party_mode(call: ServiceCall) -> None:
        enabled = bool(call.data.get("enabled", False))
        for coordinator in _iter_coordinators(hass):
            await coordinator.async_set_party_mode(enabled)

    async def _handle_set_auto_enabled(call: ServiceCall) -> None:
        enabled = bool(call.data.get("enabled", False))
        for coordinator in _iter_coordinators(hass):
            await coordinator.async_set_auto_enabled(enabled)

    async def _handle_set_manual_block(call: ServiceCall) -> None:
        cover_id = str(call.data.get("entity_id", "")).strip()
        if not cover_id:
            return
        duration_raw = call.data.get("duration")
        duration = int(duration_raw) if duration_raw is not None else None
        reason = call.data.get("reason")
        for coordinator in _match_coordinators_by_cover(hass, cover_id):
            await coordinator.async_set_manual_block(
                cover_id,
                duration=duration,
                reason=str(reason) if reason is not None else None,
            )

    async def _handle_clear_manual_block(call: ServiceCall) -> None:
        cover_id = str(call.data.get("entity_id", "")).strip()
        if not cover_id:
            return
        for coordinator in _match_coordinators_by_cover(hass, cover_id):
            await coordinator.async_clear_manual_block(cover_id)

    hass.services.async_register(DOMAIN, _SERVICE_SET_PARTY_MODE, _handle_set_party_mode)
    hass.services.async_register(DOMAIN, _SERVICE_SET_AUTO_ENABLED, _handle_set_auto_enabled)
    hass.services.async_register(DOMAIN, _SERVICE_SET_MANUAL_BLOCK, _handle_set_manual_block)
    hass.services.async_register(DOMAIN, _SERVICE_CLEAR_MANUAL_BLOCK, _handle_clear_manual_block)
    runtimes["_services_registered"] = True


def _async_unregister_services(hass: HomeAssistant) -> None:
    for service in _REGISTERED_SERVICES:
        hass.services.async_remove(DOMAIN, service)
    hass.data.setdefault(DOMAIN, {})["_services_registered"] = False
