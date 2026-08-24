"""Fetcher seguro da Trading Economics usando configuração RC15 (RC16)."""

from __future__ import annotations

from urllib.parse import urlsplit

from economic_context.economic_calendar_http_adapter import (
    EconomicCalendarHttpAdapter,
)
from economic_context.trading_economics_config import TradingEconomicsConfig


class TradingEconomicsCalendarFetcher:
    """Monta uma requisição somente leitura; segredo existe apenas durante a chamada."""

    NAME = "TradingEconomicsCalendarFetcher"
    VERSION = "RC16"
    CALENDAR_PATH = "/calendar/country/brazil,united%20states"

    def __init__(
        self,
        config,
        *,
        transport=None,
        max_response_bytes=1_000_000,
    ):
        if not isinstance(config, TradingEconomicsConfig):
            raise TypeError("config deve ser TradingEconomicsConfig.")
        self.config = config
        self.transport = transport
        self.max_response_bytes = int(max_response_bytes)
        if self.max_response_bytes <= 0:
            raise ValueError("max_response_bytes deve ser positivo.")
        self.last_diagnostics = {
            **config.diagnostics(),
            "status": "DISABLED" if not config.ready else "NOT_RUN",
        }

    def __call__(self, *, now):
        if not self.config.ready:
            self.last_diagnostics = {
                **self.config.diagnostics(),
                "status": "DISABLED",
            }
            raise PermissionError("Trading Economics não está habilitada.")

        endpoint = f"{self.config.base_url}{self.CALENDAR_PATH}"
        host = urlsplit(self.config.base_url).hostname
        adapter = EconomicCalendarHttpAdapter(
            endpoint,
            allowed_hosts={host},
            sensitive_query_params={
                "c": self.config.authorization_value(),
                "f": "json",
            },
            timeout_seconds=self.config.timeout_seconds,
            max_response_bytes=self.max_response_bytes,
            transport=self.transport,
        )
        try:
            events = adapter(now=now)
        except Exception:
            self.last_diagnostics = {
                **self.config.diagnostics(),
                "status": adapter.last_diagnostics.get("status", "FETCH_ERROR"),
                "source": adapter.last_diagnostics.get("source"),
                "error_type": adapter.last_diagnostics.get("error_type"),
            }
            raise

        self.last_diagnostics = {
            **self.config.diagnostics(),
            "status": "OK",
            "source": adapter.last_diagnostics.get("source"),
            "final_source": adapter.last_diagnostics.get("final_source"),
            "event_count": len(events),
        }
        return events
