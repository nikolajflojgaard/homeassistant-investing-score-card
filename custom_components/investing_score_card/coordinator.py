"""Coordinator for Investing Score Card."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InvestingScoreCardApi, InvestingScoreCardApiError
from .storage import InvestingScoreCardStore

_LOGGER = logging.getLogger(__name__)


class InvestingScoreCardCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinates weekly data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.api = InvestingScoreCardApi(hass)
        self.store = InvestingScoreCardStore(hass, entry.entry_id)
        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"investing_score_card_{entry.entry_id}",
            update_interval=timedelta(days=7),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            snapshot = await self.api.async_get_snapshot()
            await self.store.async_save_snapshot(snapshot)
            return snapshot
        except InvestingScoreCardApiError as err:
            stored = await self.store.async_load()
            if stored.snapshot:
                _LOGGER.warning("Using cached snapshot due to update error: %s", err)
                return stored.snapshot
            raise UpdateFailed(str(err)) from err
        except Exception as err:  # noqa: BLE001
            stored = await self.store.async_load()
            if stored.snapshot:
                _LOGGER.warning("Using cached snapshot due to unexpected error: %s", err)
                return stored.snapshot
            raise UpdateFailed(str(err)) from err
