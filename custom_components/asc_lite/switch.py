"""Switch entities for ASC Lite helper toggles."""

from __future__ import annotations

from typing import Any

from .const import DOMAIN

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import EntityCategory
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.components.switch import SwitchEntity
except ModuleNotFoundError:  # pragma: no cover - import-safe for local tests
    ConfigEntry = Any  # type: ignore[assignment]
    HomeAssistant = Any  # type: ignore[assignment]
    AddEntitiesCallback = Any  # type: ignore[assignment]

    class EntityCategory:  # type: ignore[no-redef]
        DIAGNOSTIC = "diagnostic"

    class SwitchEntity:  # type: ignore[no-redef]
        pass


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ASC Lite helper mirror switches from one config entry."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not runtime:
        return

    config = runtime.get("config")
    if config is None:
        return

    entities: list[SwitchEntity] = []
    if config.auto_enabled_entity_id:
        entities.append(
            ASCLiteHelperSwitch(
                entry_id=entry.entry_id,
                helper_entity_id=config.auto_enabled_entity_id,
                label="auto enabled",
                suffix="auto_enabled",
            )
        )
    if config.party_mode_entity_id:
        entities.append(
            ASCLiteHelperSwitch(
                entry_id=entry.entry_id,
                helper_entity_id=config.party_mode_entity_id,
                label="party mode",
                suffix="party_mode",
            )
        )

    async_add_entities(entities)


class ASCLiteHelperSwitch(SwitchEntity):
    """Mirror a configured helper boolean as an ASC Lite integration switch."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(self, *, entry_id: str, helper_entity_id: str, label: str, suffix: str) -> None:
        self._helper_entity_id = helper_entity_id
        self._attr_unique_id = f"{entry_id}_{suffix}"
        self._attr_name = label
        self._attr_translation_key = suffix
        self._attr_extra_state_attributes = {"helper_entity_id": helper_entity_id}

    @property
    def is_on(self) -> bool:
        state = self.hass.states.get(self._helper_entity_id)
        if state is None:
            return False
        return state.state.strip().lower() in {"on", "true", "1", "home", "present"}

    async def async_turn_on(self, **kwargs: Any) -> None:
        _ = kwargs
        await self.hass.services.async_call(
            "homeassistant",
            "turn_on",
            {"entity_id": self._helper_entity_id},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        _ = kwargs
        await self.hass.services.async_call(
            "homeassistant",
            "turn_off",
            {"entity_id": self._helper_entity_id},
            blocking=True,
        )


def build_switch_descriptors(
    *,
    cover_id: str,
    auto_enabled_entity_id: str | None = None,
    party_mode_entity_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return metadata descriptors for optional switch-like helpers.

    The descriptors are intentionally lightweight and independent from Home
    Assistant entity classes so they can be exercised in unit tests and dry runs.
    """
    switches: list[dict[str, Any]] = []

    if auto_enabled_entity_id:
        switches.append(
            {
                "name": "auto_enabled",
                "cover_id": cover_id,
                "entity_id": auto_enabled_entity_id,
                "enabled": True,
            }
        )

    if party_mode_entity_id:
        switches.append(
            {
                "name": "party_mode",
                "cover_id": cover_id,
                "entity_id": party_mode_entity_id,
                "enabled": True,
            }
        )

    return switches
