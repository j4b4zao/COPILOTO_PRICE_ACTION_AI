"""FMP quote transport for observational external-market collection.

RC1 is explicit, inert at construction, and injectable for offline tests.
It knows provider symbols only. Canonical asset mapping and per-asset routing
remain separate responsibilities.

FMP quote timestamps are Unix seconds. RC1 converts them explicitly to a
timezone-aware UTC ISO-8601 string so downstream freshness/skew checks never
need to infer a timezone.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class FMPQuoteTransport:
    NAME = "FMPQuoteTransport"
    VERSION = "RC1"
    BASE_URL = "https://financialmodelingprep.com/stable/quote"

    def __init__(self, *, api_key: str, timeout: float = 5.0, opener=None):
        self._api_key = str(api_key or "").strip()
        if not self._api_key:
            raise ValueError("api_key is required")
        self._timeout = float(timeout)
        if self._timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self._opener = opener or urlopen

    @staticmethod
    def _normalize_payload(payload):
        if not isinstance(payload, list) or len(payload) != 1:
            return None
        quote = payload[0]
        return quote if isinstance(quote, dict) else None

    @staticmethod
    def _normalize_timestamp(value):
        if isinstance(value, bool):
            return None
        try:
            unix_seconds = float(value)
        except (TypeError, ValueError):
            return None
        if unix_seconds <= 0:
            return None
        try:
            observed_at = datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
        return observed_at.isoformat()

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
            payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

        quote = self._normalize_payload(payload)
        if quote is None:
            return None

        returned_symbol = str(quote.get("symbol") or "").strip()
        if returned_symbol != symbol:
            return None

        try:
            price = float(quote["price"])
            percent_change = float(quote["changePercentage"])
        except (KeyError, TypeError, ValueError):
            return None

        timestamp = self._normalize_timestamp(quote.get("timestamp"))
        if price <= 0 or timestamp is None:
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
            "timestamp_semantics": "provider_unix_seconds_to_utc_iso8601",
            "observational_only": True,
        }
