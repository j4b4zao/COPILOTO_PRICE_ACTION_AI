"""Manual Finnhub quote candidate probe RC1.

Evidence-only follow-up to the real Forex catalog probe. The two candidates
below come from provider catalog evidence; they are still not approved mappings.
This tool checks quote availability and timestamp evidence only.

Run:
    python -m tools.finnhub_real_quote_candidate_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://finnhub.io/api/v1/quote"
CANDIDATES = {
    "DXY": "CAPITAL:DXY",
    "OIL": "OANDA:WTICO_USD",
}
SAFE_FIELDS = ("c", "d", "dp", "h", "l", "o", "pc", "t")


def _probe(api_key, internal_asset, candidate, opener=urlopen):
    url = f"{BASE_URL}?{urlencode({'symbol': candidate, 'token': api_key})}"
    request = Request(
        url,
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=15.0)
        payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return {
            "internal_asset": internal_asset,
            "candidate": candidate,
            "probe_status": "HTTP_ERROR",
            "error": f"HTTP_{exc.code}",
            "provider_fields": {},
        }
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
    try:
        price = float(payload.get("c"))
        timestamp = float(payload.get("t"))
    except (TypeError, ValueError):
        price = 0.0
        timestamp = 0.0

    valid = price > 0 and timestamp > 0
    return {
        "internal_asset": internal_asset,
        "candidate": candidate,
        "probe_status": "QUOTE_RETURNED" if valid else "NO_VALID_QUOTE",
        "error": "" if valid else str(payload.get("error") or ""),
        "provider_fields": fields,
    }


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("FINNHUB_API_KEY is required")

    return {
        "name": "FinnhubRealQuoteCandidateProbe",
        "version": "RC1",
        "provider": "Finnhub",
        "observational_only": True,
        "candidate_aliases_are_approved_mappings": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_routes": False,
        "results": [
            _probe(key, asset, candidate, opener=opener)
            for asset, candidate in CANDIDATES.items()
        ],
    }


def main():
    api_key = os.getenv("FINNHUB_API_KEY", "")
    if not api_key.strip():
        print("ERROR: FINNHUB_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
