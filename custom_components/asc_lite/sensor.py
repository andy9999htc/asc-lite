"""Diagnostic sensors for ASC Lite runtime state."""

from __future__ import annotations

from typing import Any

from .const import DOMAIN

try:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity import EntityCategory
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.components.sensor import SensorEntity
except ModuleNotFoundError:  # pragma: no cover - import-safe for local tests
    ConfigEntry = Any  # type: ignore[assignment]
    HomeAssistant = Any  # type: ignore[assignment]
    AddEntitiesCallback = Any  # type: ignore[assignment]

    class EntityCategory:  # type: ignore[no-redef]
        DIAGNOSTIC = "diagnostic"

    class SensorEntity:  # type: ignore[no-redef]
        pass


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ASC Lite diagnostic sensors from one config entry."""
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not runtime:
        return

    coordinator = runtime.get("coordinator")
    config = runtime.get("config")
    if coordinator is None or config is None:
        return

    entities: list[SensorEntity] = []
    for cover in config.covers:
        entities.extend(
            [
                ASCLiteRuleIdSensor(entry.entry_id, coordinator, cover.entity_id, cover.name),
                ASCLiteReasonCodeSensor(entry.entry_id, coordinator, cover.entity_id, cover.name),
                ASCLiteManualBlockSensor(entry.entry_id, coordinator, cover.entity_id, cover.name),
            ]
        )

    async_add_entities(entities)


class _ASCLiteBaseDiagnosticSensor(SensorEntity):
    """Base class for coordinator-backed diagnostic sensors."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry_id: str,
        coordinator: Any,
        cover_id: str,
        cover_name: str,
        sensor_key: str,
        suffix: str,
        label: str,
    ) -> None:
        self._entry_id = entry_id
        self._coordinator = coordinator
        self._cover_id = cover_id
        self._sensor_key = sensor_key
        slug = cover_id.replace(".", "_")
        self._attr_unique_id = f"{entry_id}_{slug}_{suffix}"
        self._attr_name = f"{cover_name} {label}"
        self._attr_translation_key = suffix
        self._attr_extra_state_attributes = {"cover_id": cover_id}
        self._unsub_listener = None

    @property
    def native_value(self) -> Any:
        state = self._coordinator.get_cover_runtime_state(self._cover_id)
        return getattr(state, self._sensor_key)

    async def async_added_to_hass(self) -> None:
        self._unsub_listener = self._coordinator.add_listener(self._handle_coordinator_update)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub_listener is not None:
            self._unsub_listener()
            self._unsub_listener = None

    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class ASCLiteRuleIdSensor(_ASCLiteBaseDiagnosticSensor):
    def __init__(self, entry_id: str, coordinator: Any, cover_id: str, cover_name: str) -> None:
        super().__init__(
            entry_id,
            coordinator,
            cover_id,
            cover_name,
            sensor_key="rule_id",
            suffix="last_rule_id",
            label="last rule",
        )


class ASCLiteReasonCodeSensor(_ASCLiteBaseDiagnosticSensor):
    def __init__(self, entry_id: str, coordinator: Any, cover_id: str, cover_name: str) -> None:
        super().__init__(
            entry_id,
            coordinator,
            cover_id,
            cover_name,
            sensor_key="reason_code",
            suffix="last_reason_code",
            label="last reason",
        )


class ASCLiteManualBlockSensor(_ASCLiteBaseDiagnosticSensor):
    def __init__(self, entry_id: str, coordinator: Any, cover_id: str, cover_name: str) -> None:
        super().__init__(
            entry_id,
            coordinator,
            cover_id,
            cover_name,
            sensor_key="result",
            suffix="manual_block_active",
            label="manual block active",
        )

    @property
    def native_value(self) -> Any:
        state = self._coordinator.get_cover_runtime_state(self._cover_id)
        return bool(str(state.reason_code).upper() == "MANUAL_BLOCK_ACTIVE")


def build_diagnostic_sensor_values(
    *,
    cover_id: str,
    last_decision_rule: str | None = None,
    last_decision_reason: str | None = None,
    manual_block_active: bool = False,
) -> dict[str, Any]:
    """Return stable diagnostic values for a shutter.

    The values are designed to be consumed by Home Assistant sensor entities and
    remain easy to inspect in local dry runs.
    """
    return {
        "cover_id": cover_id,
        "last_decision_rule": last_decision_rule or "unknown",
        "last_decision_reason": last_decision_reason or "unknown",
        "manual_block_active": bool(manual_block_active),
    }
