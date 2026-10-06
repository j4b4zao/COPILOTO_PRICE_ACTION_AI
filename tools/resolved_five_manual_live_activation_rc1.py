"""Manual live activation for the resolved-five observational chain RC1.

Caller-controlled only. This tool may read credentials from explicit CLI arguments
or named environment variables because the operator invokes it directly. Core
configuration/builders remain environment-free. No Bot/Score/Risk/Decision/Alert
integration is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os

from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.resolved_five_observational_configuration import (
    build_resolved_five_observational_router,
    snapshot as configuration_snapshot,
)


def _aware_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("reference timestamp must be timezone-aware")
    return parsed


def run(*, enabled: bool, reference_timestamp: str, maximum_staleness_seconds: float,
        fmp_api_key: str, twelvedata_api_key: str) -> dict:
    if enabled is not True:
        raise PermissionError("manual live observational activation requires --enable")
    reference = _aware_timestamp(reference_timestamp)
    if maximum_staleness_seconds <= 0:
        raise ValueError("maximum staleness must be positive")
    if not fmp_api_key or not twelvedata_api_key:
        raise ValueError("explicit FMP and Twelve Data API keys are required")

    router = build_resolved_five_observational_router(
        fmp_api_key=fmp_api_key,
        twelvedata_api_key=twelvedata_api_key,
    )
    collector = ExternalMarketCollector(provider=router, preserve_quotes=True)
    state = collector.collect()
    snapshot = collector.observational_snapshot
    if snapshot is None:
        raise RuntimeError("observational snapshot was not produced")
    audit = snapshot.audit(
        reference_timestamp=reference,
        maximum_staleness_seconds=maximum_staleness_seconds,
    )
    assets = {
        item.canonical_symbol: {
            "status": item.status,
            "price": item.price,
            "change": item.change,
            "timestamp": item.original_timestamp,
            "provider": item.provider_name,
            "provider_symbol": item.provider_symbol,
            "reasons": list(item.reasons),
        }
        for item in audit.assets
    }
    return {
        "name": "ResolvedFiveManualLiveActivation",
        "version": "RC1",
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "reference_timestamp": reference.isoformat(),
        "maximum_staleness_seconds": maximum_staleness_seconds,
        "configuration": configuration_snapshot(),
        "collector_state_valid": state.valid,
        "collector_reasons": list(state.reasons),
        "readiness": {
            "status": audit.readiness.status,
            "available_assets": list(audit.readiness.available_assets),
            "missing_assets": list(audit.readiness.missing_assets),
            "stale_assets": list(audit.readiness.stale_assets),
            "maximum_observed_skew_seconds": audit.readiness.maximum_observed_skew_seconds,
        },
        "assets": assets,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--reference-timestamp", required=True)
    parser.add_argument("--maximum-staleness-seconds", type=float, default=3600.0)
    parser.add_argument("--fmp-api-key", default=None)
    parser.add_argument("--twelvedata-api-key", default=None)
    args = parser.parse_args()

    # Environment reads are intentionally confined to this explicitly invoked tool.
    fmp_key = args.fmp_api_key or os.environ.get("FMP_API_KEY", "")
    td_key = args.twelvedata_api_key or os.environ.get("TWELVEDATA_API_KEY", "")
    result = run(
        enabled=args.enable,
        reference_timestamp=args.reference_timestamp,
        maximum_staleness_seconds=args.maximum_staleness_seconds,
        fmp_api_key=fmp_key,
        twelvedata_api_key=td_key,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
