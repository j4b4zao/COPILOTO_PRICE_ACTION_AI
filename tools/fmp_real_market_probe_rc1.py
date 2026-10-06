"""Manual FMP direct market candidate probe RC1.

Evidence-only. Candidate aliases are hypotheses, not approved mappings.
The tool records provider identity, availability, plan/error evidence and
timestamp metadata without creating ProviderSymbolMap, manifest, adapter,
Bot integration, or trading influence.

Run:
    python -m tools.fmp_real_market_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://financialmodelingprep.com/stable/quote"
CANDIDATES = {
    "US500": ("^GSPC",),
    "NASDAQ": ("^IXIC",),
    "DXY": ("DX-Y.NYB", "DXY"),
    "VIX": ("^VIX",),
    "OIL": ("CLUSD", "CL=F"),
}
SAFE_FIELDS = (
    "symbol", "name", "price", "change", "changePercentage",
    "timestamp", "exchange", "exchangeFullName", "currency",
    "volume", "previousClose", "open", "dayLow", "dayHigh",
    "yearLow", "yearHigh", "error", "Error Message", "message",
)


def _safe_payload(payload):
    if isinstance(payload, list):
        if not payload:
            return {}, True
        first = payload[0]
        return (first, False) if isinstance(first, dict) else ({}, True)
    if isinstance(payload, dict):
        return payload, False
    return {}, True


def _probe(api_key, internal_asset, candidate, opener=urlopen):
    symbol = quote(candidate, safe="")
    url = f"{BASE_URL}?{urlencode({'symbol': candidate, 'apikey': api_key})}"
    request = Request(
        url,
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=15.0)
        payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            payload = {"error": "HTTPError", "message": str(exc.code)}
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "internal_asset": internal_asset,
            "candidate": candidate,
            "probe_status": "REQUEST_ERROR",
            "error": type(exc).__name__,
            "provider_fields": {},
        }

    fields_payload, invalid = _safe_payload(payload)
    if invalid:
        return {
            "internal_asset": internal_asset,
            "candidate": candidate,
            "probe_status": "INVALID_OR_EMPTY_PAYLOAD",
            "error": "",
            "provider_fields": {},
        }

    fields = {key: fields_payload.get(key) for key in SAFE_FIELDS if key in fields_payload}
    error_text = str(
        fields_payload.get("error")
        or fields_payload.get("Error Message")
        or fields_payload.get("message")
        or ""
    )
    has_quote = fields_payload.get("price") is not None and fields_payload.get("symbol") is not None
    return {
        "internal_asset": internal_asset,
        "candidate": candidate,
        "probe_status": "QUOTE_RETURNED" if has_quote else "PROVIDER_ERROR",
        "error": "" if has_quote else error_text,
        "provider_fields": fields,
    }


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("FMP_API_KEY is required")

    results = []
    for asset, candidates in CANDIDATES.items():
        for candidate in candidates:
            results.append(_probe(key, asset, candidate, opener=opener))

    return {
        "name": "FMPRealMarketProbe",
        "version": "RC1",
        "provider": "Financial Modeling Prep",
        "observational_only": True,
        "candidate_aliases_are_approved_mappings": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_routes": False,
        "us10y_intentionally_excluded": True,
        "results": results,
    }


def main():
    api_key = os.getenv("FMP_API_KEY", "")
    if not api_key.strip():
        print("ERROR: FMP_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
