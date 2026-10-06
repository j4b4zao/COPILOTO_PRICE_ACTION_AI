"""Twelve Data quote transport for the configured observational adapter.

RC1 is explicit and injectable: construction requires an API key, performs no
request, and accepts an opener for offline tests. It knows provider symbols only;
canonical asset mapping remains the manifest/adapter responsibility.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TwelveDataQuoteTransport:
    NAME = "TwelveDataQuoteTransport"
    VERSION = "RC1"
    BASE_URL = "https://api.twelvedata.com/quote"

    def __init__(self, *, api_key: str, timeout: float = 5.0, opener=None):
        self._api_key = str(api_key or "").strip()
        if not self._api_key:
            raise ValueError("api_key is required")
        self._timeout = float(timeout)
        if self._timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self._opener = opener or urlopen

    def fetch(self, provider_symbol: str):
        symbol = str(provider_symbol or "").strip()
        if not symbol:
            raise ValueError("provider_symbol is required")

        url = f"{self.BASE_URL}?{urlencode({'symbol': symbol, 'apikey': self._api_key})}"
        request = Request(
            url,
            headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
            method="GET",
        )

        try:
            response = self._opener(request, timeout=self._timeout)
            raw = response.read()
            payload = json.loads(raw.decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(payload, dict) or payload.get("status") == "error":
            return None

        try:
            price = float(payload["close"])
            percent_change = float(payload["percent_change"])
        except (KeyError, TypeError, ValueError):
            return None

        if price <= 0:
            return None

        timestamp = payload.get("datetime", "")
        return {
            "price": price,
            "change": percent_change,
            "timestamp": "" if timestamp is None else str(timestamp),
        }

    def snapshot(self):
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "base_url": self.BASE_URL,
            "timeout": self._timeout,
            "configured": True,
            "observational_only": True,
        }
