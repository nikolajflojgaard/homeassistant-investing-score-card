"""API layer for Investing Score Card."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .engine import build_snapshot


class InvestingScoreCardApiError(Exception):
    """Raised for API failures."""


class InvestingScoreCardApi:
    """HA wrapper for the scoring engine."""

    def __init__(self, hass: HomeAssistant, settings: dict | None = None) -> None:
        self._hass = hass
        self._settings = settings or {}

    async def async_get_snapshot(self) -> dict:
        """Compute latest snapshot in executor."""
        try:
            return await self._hass.async_add_executor_job(build_snapshot, self._settings)
        except Exception as err:  # noqa: BLE001
            raise InvestingScoreCardApiError(str(err)) from err
