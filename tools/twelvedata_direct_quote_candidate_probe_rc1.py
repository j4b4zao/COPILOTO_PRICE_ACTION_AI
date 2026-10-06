"""Manual Twelve Data direct quote candidate probe RC1.

Evidence-only. Candidate aliases are hypotheses, not approved mappings.
The tool records provider identity and timestamp metadata without creating
ProviderSymbolMap, manifest, adapter, Bot integration, or trading influence.

Run:
    python -m tools.twelvedata_direct_quote_candidate_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.twelvedata.com/quote"
CANDIDATES = {
    "US500": ("SPX",),
    "NASDAQ": ("IXIC",),
    "DXY": ("DXY",),
    "VIX": ("VIX",),
    "US10Y": ("US10Y",),
    "OIL": ("WTI/USD",),
    "GOLD": ("XAU/USD",),
}
SAFE_FIELDS = (
    "symbol", "name", "exchange", "mic_code", "currency",
    "datetime", "timestamp", "last_quote_at", "close",
    "percent_change", "is_market_open", "timezone",
    "exchange_timezone", "type", "status", "code", "message",
)


def _probe(api_key, internal_asset, candidate, opener=urlopen):
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
            payload = {"status": "error", "code": exc.code, "message": "HTTPError"}
    except (URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "internal_asset": internal_asset,
            "candidate": candidate,
            "probe_status": "REQUEST_ERROR",
            "error": type(exc).__name__,
            "provider_fields": {},
        }

    if not isinstance(payload, dict):
        return {
            "internal_asset": internal_asset,
            "candidate": candidate,
            "probe_status": "INVALID_PAYLOAD",
            "error": "",
            "provider_fields": {},
        }

    fields = {key: payload.get(key) for key in SAFE_FIELDS if key in payload}
    provider_error = payload.get("status") == "error" or (
        payload.get("code") is not None and payload.get("close") is None
    )
    return {
        "internal_asset": internal_asset,
        "candidate": candidate,
        "probe_status": "PROVIDER_ERROR" if provider_error else "QUOTE_RETURNED",
        "error": str(payload.get("message") or "") if provider_error else "",
        "provider_fields": fields,
    }


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("TWELVE_DATA_API_KEY is required")

    results = []
    for asset, candidates in CANDIDATES.items():
        for candidate in candidates:
            results.append(_probe(key, asset, candidate, opener=opener))

    return {
        "name": "TwelveDataDirectQuoteCandidateProbe",
        "version": "RC1",
        "provider": "Twelve Data",
        "observational_only": True,
        "candidate_aliases_are_approved_mappings": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
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
