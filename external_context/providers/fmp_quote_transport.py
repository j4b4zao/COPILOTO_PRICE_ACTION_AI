"""FMP quote transport for observational external-market collection.

RC1 is explicit, inert at construction, and injectable for offline tests.
It knows provider symbols only. Canonical asset mapping and per-asset routing
remain separate responsibilities.

FMP quote timestamps are Unix seconds. RC1 converts them explicitly to a
timezone-aware UTC ISO-8601 string so downstream freshness/skew checks never
need to infer a timezone.
"""
from __future__ import annotations

from urllib.request import urlopen

from external_context.providers._quote_http import fetch_quote_json
from external_context.providers._quote_timeout import normalize_quote_timeout
from external_context.providers._quote_timestamp import normalize_quote_timestamp
from external_context._quote_values import normalize_quote_values


class FMPQuoteTransport:
    NAME = "FMPQuoteTransport"
    VERSION = "RC1"
    BASE_URL = "https://financialmodelingprep.com/stable/quote"

    def __init__(self, *, api_key: str, timeout: float = 5.0, opener=None):
        self._api_key = str(api_key or "").strip()
        if not self._api_key:
            raise ValueError("api_key is required")
        self._timeout = normalize_quote_timeout(timeout)
        self._opener = opener or urlopen

    @staticmethod
    def _normalize_payload(payload):
        if not isinstance(payload, list) or len(payload) != 1:
            return None
        quote = payload[0]
        return quote if isinstance(quote, dict) else None

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

        quote = self._normalize_payload(payload)
        if quote is None:
            return None

        returned_symbol = str(quote.get("symbol") or "").strip()
        if returned_symbol != symbol:
            return None

        values = normalize_quote_values(quote.get("price"), quote.get("changePercentage"))
        if values is None:
            return None
        price, percent_change = values

        timestamp = normalize_quote_timestamp(quote.get("timestamp"))
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
            "timestamp_semantics": "provider_unix_seconds_to_utc_iso8601",
            "observational_only": True,
        }
