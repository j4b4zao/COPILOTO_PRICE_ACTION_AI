"""Explicit, diagnostic-only freshness probe of the approved WTI endpoint."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from external_context.providers.americas_oil_watch_wti_transport import AmericasOilWatchWTITransport

URL = AmericasOilWatchWTITransport.URL
UPSTREAM = "Yahoo Finance (CL=F)"


def _raw_number(value):
    # Preserve invalid nonfinite numbers as text for standards-compliant JSON.
    return repr(value) if isinstance(value, float) and not math.isfinite(value) else value


def _aware(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be a timezone-aware ISO-8601 string")
    parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def run(*, enabled, reference_timestamp, maximum_staleness_seconds, opener=None):
    if enabled is not True:
        raise PermissionError("explicit --enable is required")
    reference = _aware(reference_timestamp)
    threshold = float(maximum_staleness_seconds)
    if not math.isfinite(threshold) or threshold <= 0:
        raise ValueError("maximum_staleness_seconds must be finite and greater than zero")
    result = {
        "name": "AmericasOilWatchWTIFreshnessProbe", "version": "RC1",
        "diagnostic_only": True, "operational_influence_allowed": False,
        "automatic_activation": False, "fallback_allowed": False,
        "endpoint": URL, "internal_asset": "OIL", "symbol": "CL=F",
        "symbol_basis": "configured identity; requires matching provider/dataSource",
        "reference_timestamp": reference.isoformat(),
        "maximum_staleness_seconds": threshold,
        "provider": None, "dataSource": None, "price": None, "change": None,
        "raw_observedAt": None, "timestamp": None, "age_seconds": None,
        "freshness_status": "UNAVAILABLE",
    }
    request = Request(URL, headers={"User-Agent": "COPILOTO_PRICE_ACTION_AI/ExternalContext"}, method="GET")
    try:
        response = (opener or urlopen)(request, timeout=5.0)
        try:
            # Evidence only: headers do not override observedAt or imply freshness.
            headers = getattr(response, "headers", None)
            result["raw_http_headers"] = {
                key: headers.get(key) for key in ("Date", "Age", "Cache-Control", "Last-Modified", "ETag")
                if headers is not None and headers.get(key) is not None
            }
            payload = json.loads(response.read().decode("utf-8"))
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
    except HTTPError as exc:
        result.update(request_status="HTTP_ERROR", http_status=exc.code)
        return result
    except (URLError, TimeoutError, OSError):
        result["request_status"] = "TRANSPORT_ERROR"
        return result
    except (UnicodeDecodeError, json.JSONDecodeError):
        result["request_status"] = "INVALID_JSON"
        return result
    result["request_status"] = "OK"
    if not isinstance(payload, dict):
        result["validation_status"] = "INVALID_PAYLOAD"
        return result
    result.update(provider=payload.get("provider"), dataSource=payload.get("dataSource"),
                  raw_observedAt=payload.get("observedAt"),
                  raw_quoteType=payload.get("quoteType"), raw_quoteStatus=payload.get("quoteStatus"),
                  raw_priceUsd=_raw_number(payload.get("priceUsd")), raw_changePct=_raw_number(payload.get("changePct")))
    result["raw_other_timestamps"] = {
        key: value for key, value in payload.items()
        if key != "observedAt" and (key.endswith("At") or "timestamp" in key.lower())
    }
    # The captured endpoint schema declares identity through these two fields.
    # Optional explicit symbol fields, if returned, must agree as well.
    if any(payload.get(key) != "CL=F" for key in ("symbol", "provider_symbol", "providerSymbol") if key in payload):
        result["validation_status"] = "INVALID_IDENTITY"
        return result
    if payload.get("provider") != UPSTREAM or payload.get("dataSource") != UPSTREAM:
        result["validation_status"] = "INVALID_UPSTREAM"
        return result
    if payload.get("quoteType") != "intraday" or payload.get("quoteStatus") != "current":
        result["validation_status"] = "INCOMPATIBLE_QUOTE"
        return result
    try:
        price, change = float(payload["priceUsd"]), float(payload["changePct"])
        if any(isinstance(payload[key], bool) for key in ("priceUsd", "changePct")):
            raise ValueError("boolean quote")
        if not math.isfinite(price) or not math.isfinite(change) or price <= 0:
            raise ValueError("invalid quote")
    except (KeyError, TypeError, ValueError, OverflowError):
        result["validation_status"] = "INVALID_PAYLOAD"
        return result
    result.update(price=price, change=change)
    try:
        observed = _aware(payload.get("observedAt"))
    except (TypeError, ValueError):
        result["validation_status"] = "INVALID_OBSERVED_AT"
        return result
    age = (reference - observed).total_seconds()
    result.update(validation_status="VALID", timestamp=observed.isoformat(), age_seconds=age,
                  freshness_status="FUTURE" if age < 0 else ("STALE" if age > threshold else "FRESH"))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--reference-timestamp", required=True)
    parser.add_argument("--maximum-staleness-seconds", type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(run(enabled=args.enable, reference_timestamp=args.reference_timestamp,
                         maximum_staleness_seconds=args.maximum_staleness_seconds),
                     indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()

