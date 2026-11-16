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


def test_collector_orders_provider_timestamps_by_instant():
    earlier = Provider("earlier", {
        "price": 100, "change": 0, "timestamp": "2026-10-06T13:00:00+02:00",
    })
    later = Provider("later", {
        "price": 100, "change": 0, "timestamp": "2026-10-06T12:00:00+00:00",
    })
    routes = dict.fromkeys(ExternalMarketCollector.MARKETS, earlier)
    routes["GOLD"] = later
    collector = ExternalMarketCollector(provider=ExternalPerAssetProviderRouter(routes))

    state = collector.collect()

    assert state.valid
    assert state.timestamp == "2026-10-06T12:00:00+00:00"


@pytest.mark.parametrize("asset, expected_valid", [("US500", False), ("GOLD", True)])
def test_unavailable_provider_preserves_quotes_from_other_routes(asset, expected_valid):
    unavailable = Provider("unavailable", None)
    available = Provider("available", {"price": 100, "change": 1.25})
    routes = dict.fromkeys(ExternalMarketCollector.MARKETS, available)
    routes[asset] = unavailable
    collector = ExternalMarketCollector(provider=ExternalPerAssetProviderRouter(routes))

    state = collector.collect()

    assert state.valid is expected_valid
    assert state.nasdaq == 100
    assert state.nasdaq_change == 1.25
    assert getattr(state, asset.lower()) == 0.0
    assert unavailable.calls == [asset]
    assert available.calls == [
        symbol for symbol in ExternalMarketCollector.MARKETS if symbol != asset
    ]


@pytest.mark.parametrize("price, valid", [(None, True), (100, True), (0, False), (-1, False)])
def test_partial_snapshot_validates_supplied_optional_price(price, valid):
    collector = ExternalMarketCollector()
    data = dict.fromkeys(collector.REQUIRED_FOR_CONTEXT, 100)
    if price is not None:
        data["gold"] = price

    state = collector.coletar(data, require_all_markets=False)

    assert state.valid is valid
    assert state.gold == (100 if price == 100 else 0)


def test_partial_snapshot_rejects_explicit_null_change():
    collector = ExternalMarketCollector()
    data = dict.fromkeys(collector.REQUIRED_FOR_CONTEXT, 100)
    assert collector.coletar(data, require_all_markets=False).valid

    data["us500_change"] = None
    state = collector.coletar(data, require_all_markets=False)

    assert not state.valid
    assert state.us500_change == 0.0
    assert "Variação de US500 inválida." in state.reasons


def test_partial_snapshot_rejects_explicit_null_optional_price():
    collector = ExternalMarketCollector()
    data = dict.fromkeys(collector.REQUIRED_FOR_CONTEXT, 100)
    data["gold"] = None

    state = collector.coletar(data, require_all_markets=False)

    assert not state.valid
    assert state.gold == 0.0
    assert "GOLD inválido ou ausente." in state.reasons


@pytest.mark.parametrize("price", [{}, {"gold": None}, {"gold": 0}, {"gold": "invalid"}])
def test_partial_snapshot_rejects_optional_change_without_valid_price(price):
    collector = ExternalMarketCollector()
    data = dict.fromkeys(collector.REQUIRED_FOR_CONTEXT, 100)
    data["gold_change"] = 1.25
    data.update(price)

    state = collector.coletar(data, require_all_markets=False)

    assert not state.valid
    assert state.gold_change == 0.0
    assert "Variação de GOLD inválida." in state.reasons

    data["gold"] = 100
    state = collector.coletar(data, require_all_markets=False)
    assert state.valid
    assert state.gold_change == 1.25


@pytest.mark.parametrize("field", ["price", "change"])
@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), True, False, "invalid", 10**400]
)
def test_collector_rejects_invalid_numeric_provider_and_snapshot_values(field, value):
    payload = {"price": 100, "change": 0}
    payload[field] = value
    routes = {
        asset: Provider(asset, payload if asset == "US500" else {"price": 100, "change": 0})
        for asset in ExternalMarketCollector.MARKETS
    }
    collector = ExternalMarketCollector(provider=ExternalPerAssetProviderRouter(routes))

    state = collector.collect()
    assert state.valid is False
    assert state.us500 == 0

    snapshot = {name: 100 for name in collector.FIELD_TO_SYMBOL}
    snapshot["us500" if field == "price" else "us500_change"] = value
    state = collector.coletar(snapshot)
    assert state.valid is False
    assert getattr(state, "us500" if field == "price" else "us500_change") == 0.0


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
