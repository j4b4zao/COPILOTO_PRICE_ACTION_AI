"""Manual Finnhub catalog evidence probe RC1.

Evidence-only. This tool inventories provider-exposed Forex instruments and
records matches for DXY/OIL search terms. It does not approve mappings, create
provider configuration, construct router routes, or influence trading.

US10Y is intentionally not guessed through Forex. Finnhub's documented US
government bond data is end-of-day, so RC1 reports that limitation instead of
pretending it satisfies the intraday external-context requirement.

Run:
    python -m tools.finnhub_real_catalog_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://finnhub.io/api/v1"
SEARCH_TERMS = {
    "DXY": ("DXY", "DOLLAR INDEX", "US DOLLAR INDEX"),
    "OIL": ("WTI", "CRUDE", "BRENT", "OIL"),
}
SAFE_FIELDS = ("symbol", "displaySymbol", "description")


def _get(path, api_key, params=None, opener=urlopen):
    query = dict(params or {})
    query["token"] = api_key
    request = Request(
        f"{BASE_URL}{path}?{urlencode(query)}",
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=15.0)
        return json.loads(response.read().decode("utf-8")), ""
    except HTTPError as exc:
        return None, f"HTTP_{exc.code}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def _matches(rows, terms):
    found = []
    if not isinstance(rows, list):
        return found
    for row in rows:
        if not isinstance(row, dict):
            continue
        searchable = " ".join(str(row.get(k) or "") for k in SAFE_FIELDS).upper()
        if any(term in searchable for term in terms):
            found.append({k: row.get(k) for k in SAFE_FIELDS if k in row})
    return found


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("FINNHUB_API_KEY is required")

    exchanges, exchange_error = _get("/forex/exchange", key, opener=opener)
    if not isinstance(exchanges, list):
        exchanges = []

    catalogs = []
    matches = {asset: [] for asset in SEARCH_TERMS}
    for exchange in exchanges:
        if not isinstance(exchange, str) or not exchange.strip():
            continue
        rows, error = _get(
            "/forex/symbol",
            key,
            {"exchange": exchange},
            opener=opener,
        )
        row_count = len(rows) if isinstance(rows, list) else 0
        catalogs.append({
            "exchange": exchange,
            "status": "OK" if isinstance(rows, list) else "ERROR",
            "error": error,
            "row_count": row_count,
        })
        for asset, terms in SEARCH_TERMS.items():
            for item in _matches(rows, terms):
                matches[asset].append({"exchange": exchange, **item})

    return {
        "name": "FinnhubRealCatalogProbe",
        "version": "RC1",
        "provider": "Finnhub",
        "observational_only": True,
        "candidate_aliases_are_approved_mappings": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_routes": False,
        "forex_exchange_status": "OK" if exchanges else "UNAVAILABLE",
        "forex_exchange_error": exchange_error,
        "forex_exchanges": exchanges,
        "catalogs": catalogs,
        "matches": matches,
        "US10Y": {
            "status": "NOT_PROBED_AS_INTRADAY",
            "reason": "documented US government bond data is end-of-day; no intraday identity is assumed",
        },
    }


def main():
    api_key = os.getenv("FINNHUB_API_KEY", "")
    if not api_key.strip():
        print("ERROR: FINNHUB_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
