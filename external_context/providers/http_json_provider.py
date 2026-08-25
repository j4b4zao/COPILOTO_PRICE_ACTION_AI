"""
external_context/providers/http_json_provider.py

ExternalContext RC2.2 - configurable HTTP JSON provider.

Provider real e agnóstico de fornecedor para alimentar o
ExternalMarketCollector RC2.1 sem adicionar dependências externas.

Contrato público:
    fetch(symbol) -> {"price": float, "change": float, "timestamp": str} | None

O provider não interpreta mercado, não gera BUY/SELL e não toca no núcleo
Strategy -> Score -> Risk -> Decision.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(slots=True, frozen=True)
class HttpJsonSymbolConfig:
    url: str
    price_path: str = "price"
    change_path: str = "change"
    timestamp_path: str = "timestamp"


class HttpJsonExternalMarketProvider:
    """Provider HTTP JSON configurável e sem dependências de terceiros."""

    VERSION = "RC2.2-HTTP-JSON-PROVIDER"
    DEFAULT_TIMEOUT = 5.0

    def __init__(
        self,
        symbol_configs: dict[str, HttpJsonSymbolConfig] | None = None,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        headers: dict[str, str] | None = None,
        opener=None,
    ):
        self.symbol_configs = dict(symbol_configs or self.from_environment_configs())
        self.timeout = float(timeout)
        if self.timeout <= 0:
            raise ValueError("timeout deve ser maior que zero.")
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext",
            **(headers or {}),
        }
        self._opener = opener or urlopen

    @classmethod
    def from_environment_configs(cls) -> dict[str, HttpJsonSymbolConfig]:
        """Lê URLs e caminhos JSON de variáveis de ambiente.

        Exemplo:
            EXTERNAL_US500_URL=https://provider/quote?symbol=SPX
            EXTERNAL_US500_PRICE_PATH=data.price
            EXTERNAL_US500_CHANGE_PATH=data.change_percent
            EXTERNAL_US500_TIMESTAMP_PATH=data.timestamp
        """
        configs = {}
        for symbol in ("US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD"):
            prefix = f"EXTERNAL_{symbol}_"
            url = os.getenv(prefix + "URL", "").strip()
            if not url:
                continue
            configs[symbol] = HttpJsonSymbolConfig(
                url=url,
                price_path=os.getenv(prefix + "PRICE_PATH", "price").strip() or "price",
                change_path=os.getenv(prefix + "CHANGE_PATH", "change").strip() or "change",
                timestamp_path=os.getenv(prefix + "TIMESTAMP_PATH", "timestamp").strip() or "timestamp",
            )
        return configs

    def fetch(self, symbol: str) -> dict | None:
        symbol = str(symbol or "").upper().strip()
        config = self.symbol_configs.get(symbol)
        if config is None:
            return None

        url = config.url.replace("{symbol}", quote(symbol))
        request = Request(url, headers=self.headers, method="GET")

        try:
            response = self._opener(request, timeout=self.timeout)
            raw = response.read()
        except (HTTPError, URLError, TimeoutError, OSError):
            return None

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return None

        if not isinstance(payload, (dict, list)):
            return None

        price = self._extract(payload, config.price_path)
        change = self._extract(payload, config.change_path)
        timestamp = self._extract(payload, config.timestamp_path)

        try:
            price = float(price)
            change = float(change)
        except (TypeError, ValueError):
            return None

        if price <= 0:
            return None

        return {
            "price": price,
            "change": change,
            "timestamp": "" if timestamp is None else str(timestamp),
        }

    @staticmethod
    def _extract(payload, path: str):
        """Extrai caminhos simples separados por ponto, incluindo índices de lista."""
        current = payload
        for token in str(path or "").split("."):
            if token == "":
                continue
            if isinstance(current, dict):
                if token not in current:
                    return None
                current = current[token]
            elif isinstance(current, list):
                try:
                    current = current[int(token)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current
