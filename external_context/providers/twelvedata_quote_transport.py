"""Twelve Data quote transport for the configured observational adapter.

RC1 is explicit and injectable: construction requires an API key, performs no
request, and accepts an opener for offline tests. It knows provider symbols only;
canonical asset mapping remains the manifest/adapter responsibility.
"""
from __future__ import annotations

from urllib.request import urlopen

from external_context.providers._quote_http import fetch_quote_json
from external_context.providers._quote_timeout import normalize_quote_timeout
from external_context.providers._quote_timestamp import normalize_quote_timestamp
from external_context._quote_values import normalize_quote_values


class TwelveDataQuoteTransport:
    NAME = "TwelveDataQuoteTransport"
    VERSION = "RC1"
    BASE_URL = "https://api.twelvedata.com/quote"

    def __init__(self, *, api_key: str, timeout: float = 5.0, opener=None):
        self._api_key = str(api_key or "").strip()
        if not self._api_key:
            raise ValueError("api_key is required")
        self._timeout = normalize_quote_timeout(timeout)
        self._opener = opener or urlopen

    def fetch(self, provider_symbol: str):
        symbol = str(provider_symbol or "").strip()
        if not symbol:
            raise ValueError("provider_symbol is required")

        payload = fetch_quote_json(
            self._opener,
            self.BASE_URL,
            symbol=symbol,
            api_key=self._api_key,
            timeout=self._timeout,
        )

        if not isinstance(payload, dict) or payload.get("status") == "error":
            return None
        if "symbol" in payload and payload["symbol"] != symbol:
            return None

        values = normalize_quote_values(payload.get("close"), payload.get("percent_change"))
        if values is None:
            return None
        price, percent_change = values

        timestamp = normalize_quote_timestamp(payload.get("timestamp"))
        if timestamp is None:
            return None

        return {
            "price": price,
            "change": percent_change,
            "timestamp": timestamp,
        }

    def snapshot(self):
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "base_url": self.BASE_URL,
            "timeout": self._timeout,
            "configured": True,
            "observational_only": True,
            "timestamp_semantics": "provider_unix_seconds_to_utc_iso8601",
        }
