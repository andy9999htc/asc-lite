"""Switch helper metadata for ASC Lite diagnostics and automation toggles."""

from __future__ import annotations

from typing import Any


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
