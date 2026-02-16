"""Sensor platform for Investing Score Card."""

from __future__ import annotations

import re
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import InvestingScoreCardCoordinator
from .entity import device_info_from_entry


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: InvestingScoreCardCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [TopOpportunitiesSensor(entry, coordinator), MarketSummarySensor(entry, coordinator)]

    data = coordinator.data or {}
    for asset in data.get("assets", []):
        entities.append(AssetAssessmentSensor(entry, coordinator, asset.get("name", "unknown")))

    async_add_entities(entities)


class BaseScoreSensor(CoordinatorEntity[InvestingScoreCardCoordinator], SensorEntity):
    """Base class with shared device info."""

    def __init__(self, entry: ConfigEntry, coordinator: InvestingScoreCardCoordinator) -> None:
        super().__init__(coordinator)
        name = entry.options.get(CONF_NAME, entry.data.get(CONF_NAME, DEFAULT_NAME))
        self._attr_extra_state_attributes = {"integration_name": name, "entry_id": entry.entry_id}
        self._attr_device_info = device_info_from_entry(entry)


class TopOpportunitiesSensor(BaseScoreSensor):
    """Top opportunities, sorted by opportunity score."""

    _attr_has_entity_name = True
    _attr_name = "Top Opportunities"
    _attr_icon = "mdi:podium-gold"

    def __init__(self, entry: ConfigEntry, coordinator: InvestingScoreCardCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_top_opportunities"

    @property
    def native_value(self) -> str:
        top = (self.coordinator.data or {}).get("top_opportunities", [])
        return top[0]["name"] if top else "N/A"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = dict(super().extra_state_attributes or {})
        data = self.coordinator.data or {}
        top = data.get("top_opportunities", [])
        base["generated_at"] = data.get("generated_at")
        base["top_10"] = top
        return base


class MarketSummarySensor(BaseScoreSensor):
    """Market valuation summary counts."""

    _attr_has_entity_name = True
    _attr_name = "Market Summary"
    _attr_icon = "mdi:chart-bell-curve"

    def __init__(self, entry: ConfigEntry, coordinator: InvestingScoreCardCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{entry.entry_id}_market_summary"

    @property
    def native_value(self) -> str:
        summary = (self.coordinator.data or {}).get("summary", {})
        return f"U:{summary.get('undervalued', 0)} F:{summary.get('fair', 0)} O:{summary.get('overvalued', 0)}"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = dict(super().extra_state_attributes or {})
        data = self.coordinator.data or {}
        base.update(data.get("summary", {}))
        base["generated_at"] = data.get("generated_at")
        return base


class AssetAssessmentSensor(BaseScoreSensor):
    """Per-asset detailed sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:finance"

    def __init__(self, entry: ConfigEntry, coordinator: InvestingScoreCardCoordinator, asset_name: str) -> None:
        super().__init__(entry, coordinator)
        self._asset_name = asset_name
        self._attr_name = asset_name
        self._attr_unique_id = f"{entry.entry_id}_{_slug(asset_name)}"

    def _asset(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        for item in data.get("assets", []):
            if item.get("name") == self._asset_name:
                return item
        return {}

    @property
    def native_value(self) -> str:
        return self._asset().get("assessment", "N/A")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        base = dict(super().extra_state_attributes or {})
        item = self._asset()
        base.update(
            {
                "ticker": item.get("ticker"),
                "index": item.get("index"),
                "benchmark": item.get("benchmark"),
                "price": item.get("price"),
                "fair_price": item.get("fair_price"),
                "valuation_gap_pct": item.get("valuation_gap_pct"),
                "valuation_model": item.get("valuation_model"),
                "actual_multiple": item.get("actual_multiple"),
                "fair_multiple": item.get("fair_multiple"),
                "multiple_ratio": item.get("multiple_ratio"),
                "score_total": item.get("score_total"),
                "grade": item.get("grade"),
                "opportunity_score": item.get("opportunity_score"),
                "data_completeness_pct": item.get("data_completeness_pct"),
                "components": item.get("components", {}),
                "metrics": item.get("metrics", {}),
                "latest_period": item.get("latest_period"),
                "prior_period": item.get("prior_period"),
                "generated_at": (self.coordinator.data or {}).get("generated_at"),
            }
        )
        return base
