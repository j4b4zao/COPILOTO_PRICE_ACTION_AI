"""Offline E2E: Twelve Data transport -> configured adapter -> snapshot -> audit."""
import json
from datetime import datetime, timezone

from external_context.external_context_service import ExternalContextService
from external_context.external_observational_cycle_boundary import (
    ExternalObservationalCycleBoundary,
    ExternalObservationalCyclePolicy,
)
from external_context.external_observational_manual_activation import (
    ExternalObservationalManualActivation,
)
from external_context.providers.external_configured_provider_adapter import (
    ExternalConfiguredProviderAdapter,
)
from external_context.providers.external_provider_configuration_manifest import (
    ExternalProviderConfigurationManifest,
)
from external_context.providers.twelvedata_quote_transport import (
    TwelveDataQuoteTransport,
)


SYMBOLS = {
    "US500": "SPX",
    "NASDAQ": "IXIC",
    "DXY": "DXY",
    "VIX": "VIX",
    "US10Y": "US10Y",
    "OIL": "WTI/USD",
    "GOLD": "XAU/USD",
}


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw


def symbol_map():
    return {
        "provider": "Twelve Data",
        "symbols": dict(SYMBOLS),
        "status": {asset: "MAPPED" for asset in SYMBOLS},
    }


def manifest():
    return ExternalProviderConfigurationManifest.from_symbol_map(symbol_map())


def controlled_opener(seen):
    def opener(request, timeout):
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(request.full_url).query)
        provider_symbol = query["symbol"][0]
        seen.append(provider_symbol)
        return Response({
            "symbol": provider_symbol,
            "close": "100.0",
            "percent_change": "0.25",
            "datetime": "2026-10-06T15:30:00+00:00",
        })
    return opener


def test_full_offline_chain_preserves_all_seven_provider_identities():
    seen = []
    transport = TwelveDataQuoteTransport(
        api_key="offline-test-key",
        opener=controlled_opener(seen),
    )
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)
    service = ExternalContextService(provider=adapter, observational_snapshots=True)

    state = service.snapshot()
    snapshot = service.observational_snapshot()
    audit = snapshot.audit(
        reference_timestamp=datetime(2026, 10, 6, 15, 31, tzinfo=timezone.utc),
        maximum_staleness_seconds=120,
        symbol_map=symbol_map(),
    )

    assert state.valid is True
    assert seen == list(SYMBOLS.values())
    assert len(audit.assets) == 7
    assert audit.observational_only is True
    assert audit.readiness.ready is True

    by_asset = {asset.canonical_symbol: asset for asset in audit.assets}
    for canonical, provider_symbol in SYMBOLS.items():
        asset = by_asset[canonical]
        assert asset.provider_name == "Twelve Data"
        assert asset.provider_symbol == provider_symbol
        assert asset.provider_identity_verified is True
        assert asset.identity_valid is True
        assert asset.timestamp_valid is True
        assert asset.status == "AVAILABLE"


def test_full_manual_boundary_cycle_collects_once_per_asset_and_returns_completed_audit():
    seen = []
    transport = TwelveDataQuoteTransport(
        api_key="offline-test-key",
        opener=controlled_opener(seen),
    )
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)
    boundary = ExternalObservationalCycleBoundary(provider=adapter)
    activation = ExternalObservationalManualActivation(boundary)
    policy = ExternalObservationalCyclePolicy(
        reference_timestamp=datetime(2026, 10, 6, 15, 31, tzinfo=timezone.utc),
        maximum_staleness_seconds=120,
        symbol_map=symbol_map(),
    )

    audit = activation.produce(policy, enabled=True)

    assert seen == list(SYMBOLS.values())
    assert len(seen) == 7
    assert audit.observational_only is True
    assert audit.readiness.ready is True


def test_disabled_manual_activation_performs_zero_twelve_data_requests():
    seen = []
    transport = TwelveDataQuoteTransport(
        api_key="offline-test-key",
        opener=controlled_opener(seen),
    )
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)
    boundary = ExternalObservationalCycleBoundary(provider=adapter)
    activation = ExternalObservationalManualActivation(boundary)
    policy = ExternalObservationalCyclePolicy(
        reference_timestamp=datetime(2026, 10, 6, 15, 31, tzinfo=timezone.utc),
        maximum_staleness_seconds=120,
        symbol_map=symbol_map(),
    )

    try:
        activation.produce(policy)
    except PermissionError:
        pass
    else:
        raise AssertionError("manual activation must default to disabled")

    assert seen == []


def test_timezone_naive_provider_timestamp_is_not_silently_reinterpreted():
    def opener(request, timeout):
        return Response({
            "close": "100",
            "percent_change": "0.25",
            "datetime": "2026-10-06 15:30:00",
        })

    transport = TwelveDataQuoteTransport(api_key="offline-test-key", opener=opener)
    adapter = ExternalConfiguredProviderAdapter(manifest(), transport)
    service = ExternalContextService(provider=adapter, observational_snapshots=True)

    service.snapshot()
    audit = service.observational_snapshot().audit(
        reference_timestamp=datetime(2026, 10, 6, 15, 31, tzinfo=timezone.utc),
        maximum_staleness_seconds=120,
        symbol_map=symbol_map(),
    )

    assert audit.readiness.ready is False
    assert all(asset.timestamp_valid is False for asset in audit.assets)
    assert all("INVALID_TIMESTAMP" in asset.reasons for asset in audit.assets)
