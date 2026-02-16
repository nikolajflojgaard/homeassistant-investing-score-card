"""Config flow for Investing Score Card."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_CUSTOM_TICKERS,
    CONF_INCLUDE_BENCHMARKS,
    CONF_LIST_MODE,
    CONF_NAME,
    DEFAULT_CUSTOM_TICKERS,
    DEFAULT_INCLUDE_BENCHMARKS,
    DEFAULT_LIST_MODE,
    DEFAULT_NAME,
    DOMAIN,
    LIST_MODE_CUSTOM,
    LIST_MODE_DEFAULT,
    LIST_MODE_EXTEND,
)


class InvestingScoreCardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            name = str(user_input.get(CONF_NAME, DEFAULT_NAME)).strip() or DEFAULT_NAME
            return self.async_create_entry(
                title=name,
                data={
                    CONF_NAME: name,
                    CONF_LIST_MODE: DEFAULT_LIST_MODE,
                    CONF_CUSTOM_TICKERS: DEFAULT_CUSTOM_TICKERS,
                    CONF_INCLUDE_BENCHMARKS: DEFAULT_INCLUDE_BENCHMARKS,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_NAME, default=DEFAULT_NAME): str}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return InvestingScoreCardOptionsFlow(config_entry)


class InvestingScoreCardOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        current_name = self.config_entry.options.get(CONF_NAME, self.config_entry.data.get(CONF_NAME, DEFAULT_NAME))
        current_mode = self.config_entry.options.get(
            CONF_LIST_MODE,
            self.config_entry.data.get(CONF_LIST_MODE, DEFAULT_LIST_MODE),
        )
        current_tickers = self.config_entry.options.get(
            CONF_CUSTOM_TICKERS,
            self.config_entry.data.get(CONF_CUSTOM_TICKERS, DEFAULT_CUSTOM_TICKERS),
        )
        current_bench = self.config_entry.options.get(
            CONF_INCLUDE_BENCHMARKS,
            self.config_entry.data.get(CONF_INCLUDE_BENCHMARKS, DEFAULT_INCLUDE_BENCHMARKS),
        )

        def _schema(name: str, mode: str, tickers: str, include_benchmarks: bool) -> vol.Schema:
            return vol.Schema(
                {
                    vol.Required(CONF_NAME, default=name): str,
                    vol.Required(CONF_LIST_MODE, default=mode): vol.In(
                        [LIST_MODE_DEFAULT, LIST_MODE_EXTEND, LIST_MODE_CUSTOM]
                    ),
                    vol.Optional(CONF_CUSTOM_TICKERS, default=tickers): str,
                    vol.Required(CONF_INCLUDE_BENCHMARKS, default=include_benchmarks): bool,
                }
            )

        if user_input is not None:
            name = str(user_input.get(CONF_NAME, DEFAULT_NAME)).strip() or DEFAULT_NAME
            mode = str(user_input.get(CONF_LIST_MODE, DEFAULT_LIST_MODE))
            tickers_raw = str(user_input.get(CONF_CUSTOM_TICKERS, DEFAULT_CUSTOM_TICKERS) or "").strip()
            include_benchmarks = bool(user_input.get(CONF_INCLUDE_BENCHMARKS, DEFAULT_INCLUDE_BENCHMARKS))

            if mode == LIST_MODE_CUSTOM and not tickers_raw:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_schema(name, mode, tickers_raw, include_benchmarks),
                    errors={"base": "custom_tickers_required"},
                )

            if tickers_raw:
                for part in tickers_raw.split(","):
                    ticker = part.strip().upper()
                    if not ticker:
                        continue
                    if not re.fullmatch(r"[A-Z0-9.^-]+", ticker):
                        return self.async_show_form(
                            step_id="init",
                            data_schema=_schema(name, mode, tickers_raw, include_benchmarks),
                            errors={"base": "invalid_ticker_list"},
                        )

            return self.async_create_entry(
                title="",
                data={
                    CONF_NAME: name,
                    CONF_LIST_MODE: mode,
                    CONF_CUSTOM_TICKERS: tickers_raw,
                    CONF_INCLUDE_BENCHMARKS: include_benchmarks,
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(str(current_name), str(current_mode), str(current_tickers or ""), bool(current_bench)),
        )
