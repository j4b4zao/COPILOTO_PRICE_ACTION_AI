"""Manual Massive WTI product evidence probe RC1."""
from __future__ import annotations
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.massive.com/futures/v1/products"
SAFE_FIELDS = ("product_code","name","description","exchange","exchange_code","sector","subsector","asset_class","product_type","settlement_method","currency","unit_of_measure")

def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("MASSIVE_API_KEY is required")
    query = urlencode({"product_code": "WTI", "limit": 100, "apiKey": key})
    request = Request(f"{BASE_URL}?{query}", headers={"User-Agent":"COPILOTO_PRICE_ACTION_AI/ExternalContext"}, method="GET")
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
    matches = []
    for row in rows:
        if isinstance(row, dict) and str(row.get("product_code") or "").upper() == "WTI":
            matches.append({k: row.get(k) for k in SAFE_FIELDS if k in row})
    return {
        "name":"MassiveRealWTIProductProbe","version":"RC1","provider":"Massive",
        "observational_only":True,"candidate_alias_is_approved_mapping":False,
        "creates_provider_symbol_map":False,"creates_manifest":False,
        "creates_router_route":False,"selects_futures_expiry":False,
        "request_status":"OK" if isinstance(payload, dict) else "ERROR",
        "error":error,"row_count":len(rows),"matches":matches,
    }

def main():
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key.strip():
        print("ERROR: MASSIVE_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))

if __name__ == "__main__":
    main()
