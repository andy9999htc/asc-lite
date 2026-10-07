"""Constants for ASC Lite."""

from __future__ import annotations

DOMAIN = "asc_lite"
LOGGER_NAME = "custom_components.asc_lite"

CONF_NAME = "name"
CONF_SUN_ENTITY_ID = "sun_entity_id"
CONF_PRESENCE_ENTITY_ID = "presence_entity_id"
CONF_AUTO_ENABLED_ENTITY_ID = "auto_enabled_entity_id"
CONF_PARTY_MODE_ENTITY_ID = "party_mode_entity_id"
CONF_TERRACE_WINDOW_ENTITY_ID = "terrace_window_entity_id"
CONF_OUTDOOR_TEMP_ENTITY_ID = "outdoor_temp_entity_id"
CONF_LUX_WZ_ENTITY_ID = "lux_wz_entity_id"
CONF_LUX_EZ_ENTITY_ID = "lux_ez_entity_id"

CONF_INVERT_POSITIONS_GLOBAL = "invert_positions_global"
CONF_MANUAL_BLOCK_SECONDS = "manual_block_seconds"

CONF_COVERS = "covers"
CONF_COVER_ENTITY_ID = "cover_entity_id"
CONF_COVER_NAME = "name"
CONF_COVER_SCALE = "scale"

CONF_AZIMUTH_MIN = "azimuth_min"
CONF_AZIMUTH_MAX = "azimuth_max"
CONF_ELEVATION_MIN = "elevation_min"
CONF_ELEVATION_MAX = "elevation_max"
CONF_MIN_TEMP_C = "min_temp_c"
CONF_LUX_ENTER = "lux_enter"
CONF_LUX_EXIT = "lux_exit"
CONF_HYSTERESIS_ENABLED = "hysteresis_enabled"

DEFAULT_NAME = "ASC Lite"
DEFAULT_SUN_ENTITY_ID = "sun.sun"
DEFAULT_MANUAL_BLOCK_SECONDS = 3600
DEFAULT_INVERT_POSITIONS_GLOBAL = False

ALLOWED_COVER_SCALES: set[int] = {10, 100}
