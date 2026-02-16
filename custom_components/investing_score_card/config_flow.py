"""Config flow for Investing Score Card."""

from __future__ import annotations

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
        if user_input is not None:
            name = str(user_input.get(CONF_NAME, DEFAULT_NAME)).strip() or DEFAULT_NAME
            return self.async_create_entry(
                title="",
                data={
                    CONF_NAME: name,
                    CONF_LIST_MODE: str(user_input.get(CONF_LIST_MODE, DEFAULT_LIST_MODE)),
                    CONF_CUSTOM_TICKERS: str(user_input.get(CONF_CUSTOM_TICKERS, DEFAULT_CUSTOM_TICKERS) or "").strip(),
                    CONF_INCLUDE_BENCHMARKS: bool(
                        user_input.get(CONF_INCLUDE_BENCHMARKS, DEFAULT_INCLUDE_BENCHMARKS)
                    ),
                },
            )

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
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=current_name): str,
                    vol.Required(CONF_LIST_MODE, default=current_mode): vol.In(
                        [LIST_MODE_DEFAULT, LIST_MODE_EXTEND, LIST_MODE_CUSTOM]
                    ),
                    vol.Optional(CONF_CUSTOM_TICKERS, default=str(current_tickers or "")): str,
                    vol.Required(CONF_INCLUDE_BENCHMARKS, default=bool(current_bench)): bool,
                }
            ),
        )
