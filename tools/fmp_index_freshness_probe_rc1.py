"""Manual FMP index freshness diagnostic probe RC1.

Diagnostics only. Uses the validated FMPQuoteTransport and compares each
provider timestamp with an explicit operator-supplied reference timestamp.
No implicit clock, no operational influence, no threshold mutation.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime

from external_context.providers.fmp_quote_transport import FMPQuoteTransport

SYMBOLS = ("^GSPC", "^IXIC", "^VIX")


def _parse_aware(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def run(*, enabled: bool, reference_timestamp: str, maximum_staleness_seconds: float,
        fmp_api_key: str, opener=None) -> dict:
    if enabled is not True:
        raise PermissionError("explicit --enable is required")
    threshold = float(maximum_staleness_seconds)
    if threshold <= 0:
        raise ValueError("maximum_staleness_seconds must be greater than zero")
    reference = _parse_aware(reference_timestamp)
    transport = FMPQuoteTransport(api_key=fmp_api_key, opener=opener)

    rows = []
    for symbol in SYMBOLS:
        quote = transport.fetch(symbol)
        if quote is None:
            rows.append({"symbol": symbol, "status": "UNAVAILABLE"})
            continue
        observed = _parse_aware(quote["timestamp"])
        age = (reference - observed).total_seconds()
        if age < 0:
            status = "FUTURE"
        elif age > threshold:
            status = "STALE"
        else:
            status = "FRESH"
        rows.append({
            "symbol": symbol,
            "price": quote["price"],
            "change": quote["change"],
            "provider_timestamp": quote["timestamp"],
            "reference_timestamp": reference.isoformat(),
            "age_seconds": age,
            "maximum_staleness_seconds": threshold,
            "status": status,
        })

    return {
        "name": "FMPIndexFreshnessProbe",
        "version": "RC1",
        "diagnostic_only": True,
        "operational_influence_allowed": False,
        "reference_timestamp": reference.isoformat(),
        "maximum_staleness_seconds": threshold,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--reference-timestamp", required=True)
    parser.add_argument("--maximum-staleness-seconds", type=float, default=3600.0)
    parser.add_argument("--fmp-api-key", default=None)
    args = parser.parse_args()
    result = run(
        enabled=args.enable,
        reference_timestamp=args.reference_timestamp,
        maximum_staleness_seconds=args.maximum_staleness_seconds,
        fmp_api_key=args.fmp_api_key or os.environ.get("FMP_API_KEY", ""),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
