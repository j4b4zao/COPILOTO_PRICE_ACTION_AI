"""Offline tests for partial per-asset provider configuration RC1."""
import json

import pytest

from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.external_per_asset_provider_configuration import (
    ExternalPartialConfiguredProviderAdapter,
    ExternalPerAssetProviderConfiguration,
)
from external_context.providers.external_per_asset_provider_router import (
    ExternalPerAssetProviderRouter,
)
from external_context.providers.fmp_quote_transport import FMPQuoteTransport


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._raw


FMP_SYMBOLS = {
    "US500": "^GSPC",
    "NASDAQ": "^IXIC",
    "VIX": "^VIX",
}


def test_partial_configuration_preserves_explicit_fmp_evidence_only():
    config = ExternalPerAssetProviderConfiguration.create(
        provider_name="Financial Modeling Prep",
        symbols=FMP_SYMBOLS,
    )
    snap = config.snapshot()
    assert config.provider_symbols() == FMP_SYMBOLS
    assert snap["configured_assets"] == ("US500", "NASDAQ", "VIX")
    assert set(snap["missing_assets"]) == {"DXY", "US10Y", "OIL", "GOLD"}
    assert snap["complete"] is False
    assert snap["observational_only"] is True
    assert snap["operational_influence_allowed"] is False


def test_configuration_rejects_empty_unknown_or_blank_bindings():
    with pytest.raises(ValueError, match="provider_name"):
        ExternalPerAssetProviderConfiguration.create(provider_name="", symbols={"US500": "^GSPC"})
    with pytest.raises(ValueError, match="at least one"):
        ExternalPerAssetProviderConfiguration.create(provider_name="FMP", symbols={})
    with pytest.raises(ValueError, match="unexpected"):
        ExternalPerAssetProviderConfiguration.create(provider_name="FMP", symbols={"BTC": "BTCUSD"})
    with pytest.raises(ValueError, match="non-empty"):
        ExternalPerAssetProviderConfiguration.create(provider_name="FMP", symbols={"US500": " "})


def test_adapter_maps_internal_asset_to_transport_symbol_and_injects_identity():
    calls = []
    class Transport:
        def fetch(self, symbol):
            calls.append(symbol)
            return {"price": 1, "change": 0, "timestamp": "2026-10-06T18:39:45+00:00"}

    config = ExternalPerAssetProviderConfiguration.create(
        provider_name="Financial Modeling Prep",
        symbols=FMP_SYMBOLS,
    )
    adapter = ExternalPartialConfiguredProviderAdapter(config, Transport())
    result = adapter.fetch("US500")
    assert calls == ["^GSPC"]
    assert result["provider_symbol"] == "^GSPC"
    assert result["provider_name"] == "Financial Modeling Prep"
    with pytest.raises(KeyError, match="unconfigured"):
        adapter.fetch("DXY")


def test_adapter_rejects_conflicting_transport_identity():
    class Transport:
        def fetch(self, symbol):
            return {"provider_symbol": "^IXIC", "price": 1, "change": 0}
    config = ExternalPerAssetProviderConfiguration.create(
        provider_name="Financial Modeling Prep",
        symbols={"US500": "^GSPC"},
    )
    with pytest.raises(ValueError, match="conflicts"):
        ExternalPartialConfiguredProviderAdapter(config, Transport()).fetch("US500")


def test_fmp_transport_adapter_router_collector_chain_is_partial_and_fail_closed():
    payloads = {
        "^GSPC": {"symbol": "^GSPC", "price": 7825.5, "changePercentage": 0.66, "timestamp": 1791311985},
        "^IXIC": {"symbol": "^IXIC", "price": 27639.752, "changePercentage": 0.59, "timestamp": 1791311986},
        "^VIX": {"symbol": "^VIX", "price": 15.05, "changePercentage": -3.03, "timestamp": 1791311986},
    }
    calls = []
    def opener(request, timeout):
        from urllib.parse import parse_qs, urlparse
        symbol = parse_qs(urlparse(request.full_url).query)["symbol"][0]
        calls.append(symbol)
        return Response([payloads[symbol]])

    transport = FMPQuoteTransport(api_key="offline-key", opener=opener)
    config = ExternalPerAssetProviderConfiguration.create(
        provider_name="Financial Modeling Prep",
        symbols=FMP_SYMBOLS,
    )
    adapter = ExternalPartialConfiguredProviderAdapter(config, transport)
    router = ExternalPerAssetProviderRouter({
        "US500": adapter,
        "NASDAQ": adapter,
        "VIX": adapter,
    })
    collector = ExternalMarketCollector(provider=router, preserve_quotes=True)
    state = collector.collect()

    assert calls == ["^GSPC", "^IXIC", "^VIX"]
    assert state.valid is False
    assert router.snapshot()["complete"] is False
    assert set(router.snapshot()["missing_assets"]) == {"DXY", "US10Y", "OIL", "GOLD"}
