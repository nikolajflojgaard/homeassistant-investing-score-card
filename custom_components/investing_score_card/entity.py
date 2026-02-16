"""Entity helpers for homeassistant Investing Score Card."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN


def device_info_from_entry(entry) -> DeviceInfo:
    """Create a stable DeviceInfo for entities in this integration."""
    name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME, DEFAULT_NAME))
    identifiers = {(DOMAIN, entry.entry_id)}

    return DeviceInfo(
        identifiers=identifiers,
        name=str(name),
        manufacturer="Nikolaj Flojgaard",
        model="homeassistant Investing Score Card Integration",
    )
