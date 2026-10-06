"""Manual FMP commodities catalog probe RC1.

Observational-only discovery. It asks FMP for its own commodities universe and
records oil-like rows. It does not guess an alias, approve OIL mapping, create
configuration/router state, or influence trading.
"""
from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://financialmodelingprep.com/stable/commodities-list"
SAFE_FIELDS = ("symbol", "name", "exchange", "tradeMonth")
OIL_TERMS = ("crude", "oil", "wti", "west texas", "brent")


def _oil_like(row):
    if not isinstance(row, dict):
        return False
    text = " ".join(str(row.get(k) or "") for k in ("symbol", "name")).lower()
    return any(term in text for term in OIL_TERMS)


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("FMP_API_KEY is required")

    url = f"{BASE_URL}?{urlencode({'apikey': key})}"
    request = Request(
        url,
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

    rows = payload if isinstance(payload, list) else []
    oil_rows = [
        {k: row.get(k) for k in SAFE_FIELDS if k in row}
        for row in rows if _oil_like(row)
    ]
    return {
        "name": "FMPCommoditiesCatalogProbe",
        "version": "RC1",
        "provider": "Financial Modeling Prep",
        "observational_only": True,
        "oil_candidate_is_approved_mapping": False,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "creates_router_route": False,
        "catalog_status": "OK" if isinstance(payload, list) else "ERROR",
        "error": error,
        "catalog_row_count": len(rows),
        "oil_like_row_count": len(oil_rows),
        "oil_like_rows": oil_rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    key = os.getenv("FMP_API_KEY", "")
    if not key.strip():
        print("ERROR: FMP_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
