"""Manual Massive CLF7 quote evidence probe RC1.

Observational-only. Does not approve OIL mapping, select an expiry for the
operational system, create provider configuration, or integrate with Bot.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.massive.com/futures/v1/quotes"
CANDIDATE_TICKER = "CLF7"


def _utc_iso_from_ns(value):
    if isinstance(value, bool):
        return None
    try:
        ns = int(value)
    except (TypeError, ValueError):
        return None
    if ns <= 0:
        return None
    try:
        return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def run(api_key, ticker=CANDIDATE_TICKER, opener=urlopen):
    key = str(api_key or "").strip()
    symbol = str(ticker or "").strip().upper()
    if not key:
        raise ValueError("MASSIVE_API_KEY is required")
    if not symbol:
        raise ValueError("ticker is required")

    query = urlencode({"limit": 1, "sort": "timestamp.desc", "apiKey": key})
    request = Request(
        f"{BASE_URL}/{symbol}?{query}",
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=15.0)
        payload = json.loads(response.read().decode("utf-8"))
        error = ""
    except HTTPError as exc:
        payload, error = None, f"HTTP_{exc.code}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload, error = None, type(exc).__name__

    rows = payload.get("results", []) if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []

    quote = {}
    if rows and isinstance(rows[0], dict):
        row = rows[0]
        raw_timestamp = row.get("timestamp")
        quote = {
            "ticker": row.get("ticker"),
            "bid_price": row.get("bid_price"),
            "ask_price": row.get("ask_price"),
            "bid_size": row.get("bid_size"),
            "ask_size": row.get("ask_size"),
            "session_end_date": row.get("session_end_date"),
            "timestamp_ns": raw_timestamp,
            "timestamp_utc_iso": _utc_iso_from_ns(raw_timestamp),
        }

    return {
        "name": "MassiveRealCLF7QuoteProbe",
        "version": "RC1",
        "provider": "Massive",
        "observational_only": True,
        "candidate_ticker": symbol,
        "candidate_is_approved_mapping": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_route": False,
        "selects_futures_expiry": False,
        "timestamp_semantics": "provider_unix_nanoseconds_to_utc_iso8601",
        "request_status": "OK" if isinstance(payload, dict) else "ERROR",
        "error": error,
        "row_count": len(rows),
        "quote": quote,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default=CANDIDATE_TICKER)
    args = parser.parse_args()
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key.strip():
        print("ERROR: MASSIVE_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key, args.ticker), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
