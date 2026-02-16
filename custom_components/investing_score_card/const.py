"""Constants for homeassistant Investing Score Card integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "investing_score_card"

PLATFORMS: list[Platform] = [Platform.SENSOR]

CONF_NAME = "name"
CONF_LIST_MODE = "list_mode"
CONF_CUSTOM_TICKERS = "custom_tickers"
CONF_INCLUDE_BENCHMARKS = "include_benchmarks"

DEFAULT_NAME = "homeassistant Investing Score Card"
LIST_MODE_DEFAULT = "default"
LIST_MODE_EXTEND = "extend"
LIST_MODE_CUSTOM = "custom"
DEFAULT_LIST_MODE = LIST_MODE_DEFAULT
DEFAULT_CUSTOM_TICKERS = ""
DEFAULT_INCLUDE_BENCHMARKS = True

SERVICE_REFRESH = "refresh_data"

# Optional: set to True if you want to auto-register frontend resources from frontend.py.
ENABLE_FRONTEND = False

# Dispatcher signals
SIGNAL_DATA_UPDATED = f"{DOMAIN}_data_updated"
