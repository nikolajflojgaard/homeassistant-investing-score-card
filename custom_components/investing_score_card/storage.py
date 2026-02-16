"""Persistent storage for Investing Score Card snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class StoredState:
    """Stored snapshot payload."""

    updated_at: str
    snapshot: dict[str, Any]


class InvestingScoreCardStore:
    """Store wrapper for one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, _STORAGE_VERSION, f"{DOMAIN}_{entry_id}")
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> StoredState:
        if self._data is None:
            loaded = await self._store.async_load()
            self._data = loaded if isinstance(loaded, dict) else {}
        return StoredState(
            updated_at=str(self._data.get("updated_at") or ""),
            snapshot=dict(self._data.get("snapshot") or {}),
        )

    async def async_save_snapshot(self, snapshot: dict[str, Any]) -> StoredState:
        state = StoredState(updated_at=_now_iso(), snapshot=snapshot)
        self._data = {"updated_at": state.updated_at, "snapshot": state.snapshot}
        await self._store.async_save(self._data)
        return state
