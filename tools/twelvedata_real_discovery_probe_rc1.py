"""Manual real Twelve Data discovery probe for the seven observational assets.

This script is evidence-only. It does not create ProviderSymbolMap, manifest,
configured provider, Bot integration, or trading influence.
"""
from __future__ import annotations

import json
import os

from external_context.providers.instrument_profiles import InstrumentProfiles
from external_context.providers.semantic_discovery_runner import SemanticDiscoveryRunner
from external_context.providers.semantic_symbol_resolution_pipeline import (
    SemanticSymbolResolutionPipeline,
)
from external_context.providers.twelvedata_commodity_discovery import (
    TwelveDataCommodityDiscovery,
)
from external_context.providers.twelvedata_commodity_resolution_adapter import (
    TwelveDataCommodityResolutionAdapter,
)
from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


INDEX_ASSETS = ("US500", "NASDAQ", "DXY", "VIX", "US10Y")
COMMODITY_ASSETS = ("OIL", "GOLD")
ASSETS = INDEX_ASSETS + COMMODITY_ASSETS


def _index_probe(discovery, internal_asset):
    runner = SemanticDiscoveryRunner(discovery)
    discovered = runner.search(internal_asset)
    candidates = discovered.get("results", [])
    pipeline = SemanticSymbolResolutionPipeline()
    resolved = pipeline.resolve(internal_asset, candidates)
    return {
        "internal_asset": internal_asset,
        "discovery": discovered,
        "resolution": resolved,
    }


def _commodity_probe(discovery, internal_asset):
    adapter = TwelveDataCommodityResolutionAdapter(discovery)
    resolved = adapter.resolve(internal_asset)
    return {
        "internal_asset": internal_asset,
        "discovery": {
            "status": discovery.last_status,
            "error": discovery.last_error,
            "query": discovery.last_query,
            "candidate_count": resolved.get("metadata", {}).get("candidate_count", 0),
        },
        "resolution": resolved,
    }


def run(api_key):
    api_key = str(api_key or "").strip()
    if not api_key:
        raise ValueError("TWELVE_DATA_API_KEY is required")

    symbol_discovery = TwelveDataSymbolDiscovery(api_key=api_key, timeout=10.0)
    commodity_discovery = TwelveDataCommodityDiscovery(api_key=api_key, timeout=15)

    results = []
    for asset in INDEX_ASSETS:
        results.append(_index_probe(symbol_discovery, asset))
    for asset in COMMODITY_ASSETS:
        results.append(_commodity_probe(commodity_discovery, asset))

    mapped = {
        item["internal_asset"]: item["resolution"].get("symbol")
        for item in results
        if item["resolution"].get("status") == "MAPPED"
        and item["resolution"].get("symbol")
    }
    statuses = {
        item["internal_asset"]: item["resolution"].get("status", "")
        for item in results
    }

    return {
        "name": "TwelveDataRealDiscoveryProbe",
        "version": "RC1",
        "provider": "Twelve Data",
        "observational_only": True,
        "creates_provider_symbol_map": False,
        "creates_manifest": False,
        "asset_count": len(ASSETS),
        "mapped_count": len(mapped),
        "complete": len(mapped) == len(ASSETS),
        "mapped_candidates": mapped,
        "statuses": statuses,
        "results": results,
    }


def main():
    api_key = os.getenv("TWELVE_DATA_API_KEY", "")
    if not api_key.strip():
        print("ERROR: TWELVE_DATA_API_KEY is not configured.")
        raise SystemExit(2)

    result = run(api_key)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))

    if result["complete"]:
        print("\nDISCOVERY COMPLETE: all seven assets resolved as MAPPED candidates.")
        print("No ProviderSymbolMap or manifest was created automatically.")
    else:
        print("\nDISCOVERY INCOMPLETE: automatic configuration remains blocked.")
        print("Review candidates/statuses; no symbol will be guessed.")


if __name__ == "__main__":
    main()
