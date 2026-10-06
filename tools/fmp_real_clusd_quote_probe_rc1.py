"""Manual FMP CLUSD real quote probe RC1.

CLUSD comes from the provider's own commodities catalog evidence. This probe is
observational only and does not approve OIL mapping or create router/config state.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://financialmodelingprep.com/stable/quote"
PROVIDER_SYMBOL = "CLUSD"


def _utc_iso(value):
    if isinstance(value, bool):
        return None
    try:
        seconds = int(value)
        if seconds <= 0:
            return None
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("FMP_API_KEY is required")

    url = f"{BASE_URL}?{urlencode({'symbol': PROVIDER_SYMBOL, 'apikey': key})}"
    request = Request(url, headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"}, method="GET")
    try:
        response = opener(request, timeout=15.0)
        payload = json.loads(response.read().decode("utf-8"))
        error = ""
    except HTTPError as exc:
        payload, error = None, f"HTTP_{exc.code}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload, error = None, type(exc).__name__

    row = payload[0] if isinstance(payload, list) and payload and isinstance(payload[0], dict) else {}
    timestamp = row.get("timestamp")
    quote = {}
    if row:
        quote = {
            "symbol": row.get("symbol"),
            "name": row.get("name"),
            "price": row.get("price"),
            "change": row.get("change"),
            "changePercentage": row.get("changePercentage"),
            "timestamp_unix_seconds": timestamp,
            "timestamp_utc_iso": _utc_iso(timestamp),
            "exchange": row.get("exchange"),
            "exchangeFullName": row.get("exchangeFullName"),
        }

    valid = (
        quote.get("symbol") == PROVIDER_SYMBOL
        and isinstance(quote.get("price"), (int, float))
        and not isinstance(quote.get("price"), bool)
        and quote["price"] > 0
        and quote.get("timestamp_utc_iso") is not None
    )
    return {
        "name": "FMPRealCLUSDQuoteProbe",
        "version": "RC1",
        "provider": "Financial Modeling Prep",
        "observational_only": True,
        "internal_asset": "OIL",
        "provider_symbol": PROVIDER_SYMBOL,
        "provider_symbol_source": "FMP commodities catalog",
        "candidate_is_approved_mapping": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_route": False,
        "timestamp_semantics": "provider_unix_seconds_to_utc_iso8601",
        "request_status": "OK" if isinstance(payload, list) else "ERROR",
        "quote_evidence_valid": valid,
        "error": error,
        "quote": quote,
    }


def main():
    key = os.getenv("FMP_API_KEY", "")
    if not key.strip():
        print("ERROR: FMP_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
