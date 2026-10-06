"""Contract tests for ExternalPerAssetProviderRouter RC1."""
import pytest

from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.external_per_asset_provider_router import (
    ExternalPerAssetProviderRouter,
)


class Provider:
    def __init__(self, name, payload):
        self.name = name
        self.payload = payload
        self.calls = []
    def fetch(self, asset):
        self.calls.append(asset)
        if self.payload is None:
            return None
        return dict(self.payload)


def test_routes_assets_to_distinct_injected_providers():
    gold = Provider("twelve", {"price": 10, "change": 1, "provider_name": "Twelve Data"})
    us500 = Provider("other", {"price": 20, "change": -1, "provider_name": "Other"})
    router = ExternalPerAssetProviderRouter({"GOLD": gold, "US500": us500})

    assert router.fetch("GOLD")["provider_name"] == "Twelve Data"
    assert router.fetch("US500")["provider_name"] == "Other"
    assert gold.calls == ["GOLD"]
    assert us500.calls == ["US500"]


def test_unconfigured_asset_fails_closed_as_none():
    router = ExternalPerAssetProviderRouter({})
    assert router.fetch("DXY") is None


def test_router_rejects_unknown_assets_and_invalid_providers():
    with pytest.raises(ValueError, match="unexpected"):
        ExternalPerAssetProviderRouter({"BTC": Provider("x", {})})
    with pytest.raises(TypeError, match="fetch"):
        ExternalPerAssetProviderRouter({"GOLD": object()})
    with pytest.raises(KeyError, match="unknown"):
        ExternalPerAssetProviderRouter({}).fetch("BTC")


def test_conflicting_internal_asset_fails_closed_by_exception():
    router = ExternalPerAssetProviderRouter({
        "GOLD": Provider("x", {"price": 1, "change": 0, "internal_asset": "OIL"})
    })
    with pytest.raises(ValueError, match="conflicts"):
        router.fetch("GOLD")


def test_snapshot_is_observational_and_reports_partial_coverage():
    router = ExternalPerAssetProviderRouter({
        "GOLD": Provider("x", {"price": 1, "change": 0})
    })
    snap = router.snapshot()
    assert snap["observational_only"] is True
    assert snap["operational_influence_allowed"] is False
    assert snap["complete"] is False
    assert snap["configured_assets"] == ("GOLD",)
    assert set(snap["missing_assets"]) == set(ExternalMarketCollector.MARKETS) - {"GOLD"}


def test_existing_collector_contract_accepts_router_without_changes():
    routes = {
        asset: Provider(asset, {
            "price": 100 + i,
            "change": i / 10,
            "timestamp": "2026-10-06T12:00:00+00:00",
        })
        for i, asset in enumerate(ExternalMarketCollector.MARKETS)
    }
    collector = ExternalMarketCollector(
        provider=ExternalPerAssetProviderRouter(routes),
        preserve_quotes=True,
    )
    state = collector.collect()
    assert state.valid is True
    assert all(provider.calls == [asset] for asset, provider in routes.items())
