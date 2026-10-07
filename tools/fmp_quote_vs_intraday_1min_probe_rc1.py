"""Offline-capable FMP quote vs 1-minute index freshness comparator RC1.

Diagnostic only. Compares the validated /stable/quote observation with the
latest /stable/historical-chart/1min bar for the same index symbol against an
explicit timezone-aware reference timestamp. No implicit clock and no trading
influence.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from external_context.providers.fmp_quote_transport import FMPQuoteTransport

SYMBOLS = ("^GSPC", "^IXIC", "^VIX")
INTRADAY_URL = "https://financialmodelingprep.com/stable/historical-chart/1min"


def _aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _classify(reference: datetime, observed: datetime, threshold: float) -> tuple[float, str]:
    age = (reference - observed).total_seconds()
    return age, "FUTURE" if age < 0 else ("STALE" if age > threshold else "FRESH")


def _fetch_latest_1min(symbol: str, api_key: str, opener, timeout: float = 5.0):
    url = f"{INTRADAY_URL}?{urlencode({'symbol': symbol, 'apikey': api_key})}"
    request = Request(url, headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"}, method="GET")
    try:
        response = opener(request, timeout=timeout)
        payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return {"status": "HTTP_ERROR", "http_status": exc.code}
    except (URLError, TimeoutError, OSError):
        return {"status": "TRANSPORT_ERROR"}
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "INVALID_JSON"}
    if not isinstance(payload, list):
        return {"status": "INVALID_PAYLOAD"}
    if not payload:
        return {"status": "EMPTY_PAYLOAD"}
    try:
        bars = []
        for bar in payload:
            if not isinstance(bar, dict) or not isinstance(bar.get("date"), str):
                return {"status": "INVALID_PAYLOAD"}
            raw_date = bar["date"].strip()
            observed = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            close = float(bar["close"])
            if isinstance(bar["close"], bool) or not math.isfinite(close) or close <= 0:
                return {"status": "INVALID_PAYLOAD"}
            aware = observed.tzinfo is not None and observed.utcoffset() is not None
            bars.append((observed.astimezone(timezone.utc) if aware else observed,
                         close, raw_date, aware))
        # Never compare naive wall times with absolute instants or assume order.
        if len({bar[3] for bar in bars}) != 1:
            return {"timestamp_status": "AMBIGUOUS_TIMEZONE"}
        observed, close, raw_date, aware = max(bars, key=lambda bar: bar[0])
        if not aware:
            return {"close": close, "timestamp": raw_date, "timestamp_status": "AMBIGUOUS_TIMEZONE"}
    except (KeyError, TypeError, ValueError):
        return {"status": "INVALID_PAYLOAD"}
    return {"close": close, "timestamp": observed.isoformat(), "timestamp_status": "AWARE"}


def run(*, enabled: bool, reference_timestamp: str, maximum_staleness_seconds: float,
        fmp_api_key: str, quote_opener=None, intraday_opener=None) -> dict:
    if enabled is not True:
        raise PermissionError("explicit --enable is required")
    threshold = float(maximum_staleness_seconds)
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("maximum_staleness_seconds must be finite and greater than zero")
    reference = _aware(reference_timestamp)
    quote_transport = FMPQuoteTransport(api_key=fmp_api_key, opener=quote_opener or urlopen)
    intraday_open = intraday_opener or urlopen

    rows = []
    for symbol in SYMBOLS:
        quote = quote_transport.fetch(symbol)
        minute = _fetch_latest_1min(symbol, fmp_api_key, intraday_open)
        row = {"symbol": symbol, "quote": None, "intraday_1min": minute}
        if quote is not None:
            observed = _aware(quote["timestamp"])
            age, status = _classify(reference, observed, threshold)
            row["quote"] = {**quote, "age_seconds": age, "status": status}
        if minute is not None and minute.get("timestamp_status") == "AWARE":
            observed = _aware(minute["timestamp"])
            age, status = _classify(reference, observed, threshold)
            row["intraday_1min"] = {**minute, "age_seconds": age, "status": status}
        rows.append(row)

    return {
        "name": "FMPQuoteVsIntraday1MinFreshnessComparator",
        "version": "RC1",
        "diagnostic_only": True,
        "operational_influence_allowed": False,
        "reference_timestamp": reference.isoformat(),
        "maximum_staleness_seconds": threshold,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--reference-timestamp", required=True)
    parser.add_argument("--maximum-staleness-seconds", type=float, default=3600.0)
    parser.add_argument("--fmp-api-key", default=None)
    args = parser.parse_args()
    print(json.dumps(run(
        enabled=args.enable,
        reference_timestamp=args.reference_timestamp,
        maximum_staleness_seconds=args.maximum_staleness_seconds,
        fmp_api_key=args.fmp_api_key or os.environ.get("FMP_API_KEY", ""),
    ), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
