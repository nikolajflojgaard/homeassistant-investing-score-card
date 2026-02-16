"""Constants for homeassistant Investing Score Card integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "investing_score_card"

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_NAME = "name"

DEFAULT_NAME = "homeassistant Investing Score Card"

SERVICE_REFRESH = "refresh_data"

# Optional: set to True if you want to auto-register frontend resources from frontend.py.
ENABLE_FRONTEND = False

# Dispatcher signals
SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"
