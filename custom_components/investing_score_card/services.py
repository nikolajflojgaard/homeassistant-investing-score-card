"""Services for Investing Score Card."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse

from .const import DOMAIN, SERVICE_REFRESH

_REFRESH_SCHEMA = vol.Schema({vol.Optional("entry_id"): str})


async def async_register(hass: HomeAssistant) -> None:
    async def _async_refresh(call: ServiceCall) -> ServiceResponse:
        entry_id = str(call.data.get("entry_id", "")).strip()
        coordinators = hass.data.get(DOMAIN, {})
        targets = []
        if entry_id:
            coord = coordinators.get(entry_id)
            if coord is None:
                return {"ok": False, "error": "entry_not_found"}
            targets = [coord]
        else:
            targets = [c for key, c in coordinators.items() if key not in {"services_registered"}]

        for coordinator in targets:
            await coordinator.async_request_refresh()

        return {"ok": True, "refreshed_entries": len(targets)}

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH,
            _async_refresh,
            schema=_REFRESH_SCHEMA,
            supports_response=SupportsResponse.ONLY,
        )
