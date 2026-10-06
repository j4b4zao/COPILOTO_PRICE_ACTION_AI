"""RC1 acceptance for the identity-preserving configured provider adapter."""
from unittest.mock import Mock

import pytest

from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.external_configured_provider_adapter import (
    ExternalConfiguredProviderAdapter,
)
from external_context.providers.external_provider_configuration_manifest import (
    ExternalProviderConfigurationManifest,
)


ASSETS = ExternalMarketCollector.MARKETS


def manifest():
    source = {
        "provider": "fixture-provider",
        "symbols": {asset: f"TD:{asset}" for asset in ASSETS},
        "status": {asset: "MAPPED" for asset in ASSETS},
    }
    return ExternalProviderConfigurationManifest.from_symbol_map(source)


def test_construction_is_inert_and_requires_explicit_dependencies():
    transport = Mock()
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    transport.fetch.assert_not_called()
    assert adapter.snapshot()["provider"] == "fixture-provider"

    with pytest.raises(TypeError):
        ExternalConfiguredProviderAdapter(object(), transport)
    with pytest.raises(TypeError):
        ExternalConfiguredProviderAdapter(manifest(), object())


def test_fetch_translates_internal_asset_to_validated_provider_symbol():
    transport = Mock()
    transport.fetch.return_value = {
        "price": 100,
        "change": 1,
        "timestamp": "2026-10-06T15:00:00+00:00",
    }
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    payload = adapter.fetch("US500")

    transport.fetch.assert_called_once_with("TD:US500")
    assert payload["provider_symbol"] == "TD:US500"
    assert payload["provider_name"] == "fixture-provider"


def test_payload_is_detached_before_identity_enrichment():
    raw = {"price": 100, "change": 1, "nested": {"x": 1}}
    transport = Mock()
    transport.fetch.return_value = raw
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    payload = adapter.fetch("DXY")
    payload["nested"]["x"] = 9

    assert raw == {"price": 100, "change": 1, "nested": {"x": 1}}


def test_none_remains_none_without_fabricated_identity_quote():
    transport = Mock()
    transport.fetch.return_value = None
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    assert adapter.fetch("VIX") is None


def test_invalid_transport_payload_fails_closed():
    transport = Mock()
    transport.fetch.return_value = []
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    with pytest.raises(TypeError):
        adapter.fetch("NASDAQ")


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider_symbol", "WRONG"),
        ("provider_name", "wrong-provider"),
    ],
)
def test_conflicting_transport_identity_fails_closed(field, value):
    transport = Mock()
    transport.fetch.return_value = {"price": 100, "change": 0, field: value}
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    with pytest.raises(ValueError, match="conflicts"):
        adapter.fetch("OIL")


def test_matching_transport_identity_is_preserved():
    transport = Mock()
    transport.fetch.return_value = {
        "price": 100,
        "change": 0,
        "provider_symbol": "TD:GOLD",
        "provider_name": "fixture-provider",
    }
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    payload = adapter.fetch("GOLD")

    assert payload["provider_symbol"] == "TD:GOLD"
    assert payload["provider_name"] == "fixture-provider"


def test_unknown_internal_asset_never_reaches_transport():
    transport = Mock()
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    with pytest.raises(KeyError):
        adapter.fetch("UNKNOWN")

    transport.fetch.assert_not_called()


def test_adapter_integrates_with_observational_collector_offline():
    transport = Mock()
    transport.fetch.side_effect = lambda provider_symbol: {
        "price": 100.0,
        "change": 0.25,
        "timestamp": "2026-10-06T15:00:00+00:00",
    }
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)
    collector = ExternalMarketCollector(provider=adapter, preserve_quotes=True)

    state = collector.collect()
    snapshot = collector.observational_snapshot
    quotes = snapshot.to_quotes()

    assert state.valid is True
    assert transport.fetch.call_count == len(ASSETS)
    assert set(quotes) == set(ASSETS)
    for internal_asset, quote in quotes.items():
        assert quote["provider_symbol"] == f"TD:{internal_asset}"
        assert quote["provider_name"] == "fixture-provider"


def test_adapter_owns_no_clock_cache_or_network_configuration():
    transport = Mock()
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)

    assert set(vars(adapter)) == {"_provider_name", "_symbols", "_transport"}
    transport.fetch.assert_not_called()
