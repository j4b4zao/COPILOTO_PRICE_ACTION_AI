"""Manual Massive catalog evidence probe RC1.

Evidence-only discovery for DXY and OIL. It searches Massive index reference
data for US Dollar Index/DXY evidence and futures products for WTI/Crude Oil
evidence. It does not approve mappings, select a futures expiry, create provider
configuration/router routes, or influence trading.

Run:
    python -m tools.massive_real_catalog_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.massive.com"
SAFE_INDEX_FIELDS = ("ticker", "name", "market", "type", "active", "last_updated_utc")
SAFE_PRODUCT_FIELDS = (
    "product_code", "name", "exchange", "exchange_code", "sector",
    "asset_class", "product_type", "settlement_method",
)
DXY_TERMS = ("DXY", "US DOLLAR INDEX", "U.S. DOLLAR INDEX", "DOLLAR INDEX")
OIL_TERMS = ("WTI", "WEST TEXAS", "CRUDE OIL")


def _get(path, api_key, params, opener):
    query = dict(params)
    query["apiKey"] = api_key
    request = Request(
        f"{BASE_URL}{path}?{urlencode(query)}",
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=15.0)
        payload = json.loads(response.read().decode("utf-8"))
        return payload, ""
    except HTTPError as exc:
        return None, f"HTTP_{exc.code}"
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__


def _safe_rows(payload):
    if not isinstance(payload, dict):
        return []
    rows = payload.get("results")
    return rows if isinstance(rows, list) else []


def _filter(rows, terms, fields):
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        searchable = " ".join(str(row.get(key) or "") for key in fields).upper()
        if any(term in searchable for term in terms):
            matches.append({key: row.get(key) for key in fields if key in row})
    return matches


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("MASSIVE_API_KEY is required")

    index_payload, index_error = _get(
        "/v3/reference/tickers",
        key,
        {"market": "indices", "active": "true", "search": "Dollar Index", "limit": 100},
        opener,
    )
    product_payload, product_error = _get(
        "/futures/v1/products",
        key,
        {"limit": 1000},
        opener,
    )
    index_rows = _safe_rows(index_payload)
    product_rows = _safe_rows(product_payload)

    return {
        "name": "MassiveRealCatalogProbe",
        "version": "RC1",
        "provider": "Massive",
        "observational_only": True,
        "candidate_aliases_are_approved_mappings": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_routes": False,
        "selects_futures_expiry": False,
        "DXY": {
            "request_status": "OK" if isinstance(index_payload, dict) else "ERROR",
            "error": index_error,
            "row_count": len(index_rows),
            "matches": _filter(index_rows, DXY_TERMS, SAFE_INDEX_FIELDS),
        },
        "OIL": {
            "request_status": "OK" if isinstance(product_payload, dict) else "ERROR",
            "error": product_error,
            "row_count": len(product_rows),
            "matches": _filter(product_rows, OIL_TERMS, SAFE_PRODUCT_FIELDS),
        },
        "US10Y": {
            "status": "NOT_PROBED_AS_INTRADAY",
            "reason": "Massive Treasury Yields REST dataset is documented as daily; no intraday substitution is assumed",
        },
    }


def main():
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key.strip():
        print("ERROR: MASSIVE_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
