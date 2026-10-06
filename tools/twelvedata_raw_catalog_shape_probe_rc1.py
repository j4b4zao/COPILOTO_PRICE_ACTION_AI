"""Manual raw-shape probe for Twelve Data indices and bonds endpoints.

Evidence-only diagnostic. It never creates symbol mappings or trading integration.
API keys are never emitted.

Run:
    python -m tools.twelvedata_raw_catalog_shape_probe_rc1
"""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.twelvedata.com"
PROBES = (
    ("indices", {"country": "United States", "outputsize": 5000}),
    ("bonds", {"country": "United States", "outputsize": 5000}),
)
MAX_DEPTH = 4
MAX_LIST_ITEMS = 20


def _sanitize(value, depth=0):
    if depth >= MAX_DEPTH:
        if isinstance(value, dict):
            return {"_truncated_dict_keys": list(value.keys())[:30]}
        if isinstance(value, list):
            return {"_truncated_list_length": len(value)}
        return value

    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            key_text = str(key)
            if "apikey" in key_text.lower() or "api_key" in key_text.lower():
                clean[key_text] = "<redacted>"
            else:
                clean[key_text] = _sanitize(item, depth + 1)
        return clean

    if isinstance(value, list):
        return [_sanitize(item, depth + 1) for item in value[:MAX_LIST_ITEMS]]

    return value


def _shape(value):
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": list(value.keys()),
            "children": {str(k): _shape(v) for k, v in value.items()},
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "length": len(value),
            "first_item_shape": _shape(value[0]) if value else None,
        }
    return {"type": type(value).__name__}


def _fetch(api_key, endpoint, params, opener=urlopen):
    query = dict(params)
    query["apikey"] = api_key
    url = f"{BASE_URL}/{endpoint}?{urlencode(query)}"
    request = Request(
        url,
        headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"},
        method="GET",
    )
    try:
        response = opener(request, timeout=20.0)
        raw = response.read().decode("utf-8")
        payload = json.loads(raw)
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"status": "REQUEST_ERROR", "error": type(exc).__name__}

    return {
        "status": "OK",
        "error": "",
        "payload_shape": _shape(payload),
        "sanitized_sample": _sanitize(payload),
    }


def run(api_key, opener=urlopen):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("TWELVE_DATA_API_KEY is required")

    return {
        "name": "TwelveDataRawCatalogShapeProbe",
        "version": "RC1",
        "provider": "Twelve Data",
        "observational_only": True,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "results": [
            {
                "endpoint": endpoint,
                **_fetch(key, endpoint, params, opener=opener),
            }
            for endpoint, params in PROBES
        ],
    }


def main():
    api_key = os.getenv("TWELVE_DATA_API_KEY", "")
    if not api_key.strip():
        print("ERROR: TWELVE_DATA_API_KEY is not configured.")
        raise SystemExit(2)
    print(json.dumps(run(api_key), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
