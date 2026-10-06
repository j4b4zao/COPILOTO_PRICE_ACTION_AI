"""Manual catalog probe for unresolved Twelve Data observational assets.

Explicitly invoked evidence-only tool. It queries provider reference catalogs
and never creates a ProviderSymbolMap, manifest, adapter, or Bot integration.

Run from repository root:
    python -m tools.twelvedata_real_catalog_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://api.twelvedata.com"
PROBES = (
    ("US500", "indices", {"country": "United States"}),
    ("NASDAQ", "indices", {"country": "United States"}),
    ("DXY", "indices", {"country": "United States"}),
    ("VIX", "indices", {"country": "United States"}),
    ("US10Y", "bonds", {"country": "United States"}),
)
TERMS = {
    "US500": ("s&p 500", "spx"),
    "NASDAQ": ("nasdaq composite", "ixic"),
    "DXY": ("us dollar index", "dxy", "dollar index"),
    "VIX": ("cboe volatility index", "vix"),
    "US10Y": ("10 year", "10-year", "us10y", "treasury yield 10"),
}


def _rows(payload):
    if not isinstance(payload, dict):
        return []
    for key in ("data", "list"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    result = payload.get("result")
    if isinstance(result, dict):
        for key in ("data", "list"):
            value = result.get(key)
            if isinstance(value, list):
                return value
    if isinstance(result, list):
        return result
    return []


def _matches(asset, rows):
    terms = TERMS[asset]
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        haystack = " ".join(
            str(row.get(key, ""))
            for key in ("symbol", "name", "instrument_name", "type")
        ).lower()
        if any(term in haystack for term in terms):
            matches.append(dict(row))
    return matches


def _fetch(api_key, endpoint, params, opener=urlopen):
    query = dict(params)
    query["apikey"] = api_key
    query.setdefault("outputsize", 5000)
    url = f"{BASE_URL}/{endpoint}?{urlencode(query)}"
    request = Request(
        url,
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=20.0)
        payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "REQUEST_ERROR", "error": type(exc).__name__, "rows": [], "matches": []}

    if not isinstance(payload, dict):
        return {"status": "INVALID_PAYLOAD", "error": "", "rows": [], "matches": []}
    if payload.get("status") == "error":
        return {
            "status": "PROVIDER_ERROR",
            "error": str(payload.get("message") or payload.get("code") or ""),
            "rows": [],
            "matches": [],
        }
    rows = _rows(payload)
    return {"status": "OK", "error": "", "rows": rows}


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("TWELVE_DATA_API_KEY is required")

    results = []
    for asset, endpoint, params in PROBES:
        fetched = _fetch(key, endpoint, params, opener=opener)
        rows = fetched.pop("rows", [])
        results.append({
            "internal_asset": asset,
            "endpoint": endpoint,
            "query": dict(params),
            "status": fetched["status"],
            "error": fetched["error"],
            "catalog_row_count": len(rows),
            "matches": _matches(asset, rows),
        })

    return {
        "name": "TwelveDataRealCatalogProbe",
        "version": "RC1",
        "provider": "Twelve Data",
        "observational_only": True,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "unresolved_asset_count": len(PROBES),
        "results": results,
    }


def main():
    api_key = os.getenv("TWELVE_DATA_API_KEY", "")
    if not api_key.strip():
        print("ERROR: TWELVE_DATA_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
