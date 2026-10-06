"""RC1 producer lifecycle: same-collection, explicit-policy, no runtime wiring."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from analysis.research.intermarket_external_context_bridge import (
    IntermarketExternalContextBridge as Bridge,
)
from external_context.external_context_service import ExternalContextService
from external_context.external_observational_producer_lifecycle import (
    ExternalObservationalProducerLifecycle,
)
from external_context.providers.provider_symbol_map import ProviderSymbolMap


NOW = datetime(2026, 10, 6, 15, tzinfo=timezone.utc)


def quotes():
    return {
        symbol: dict(
            price=100.0,
            change=0.0,
            timestamp=NOW.isoformat(),
            provider_symbol=symbol,
            provider_name="fixture",
        )
        for symbol in Bridge.SYMBOLS
    }


def service_for(data):
    provider = Mock()
    provider.fetch.side_effect = lambda symbol: data.get(symbol)
    service = ExternalContextService(
        provider=provider,
        observational_snapshots=True,
    )
    return provider, service


def test_one_produce_one_collection_and_same_snapshot_audit():
    data = quotes()
    provider, service = service_for(data)
    lifecycle = ExternalObservationalProducerLifecycle(service)

    audit = lifecycle.produce(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
    )

    assert provider.fetch.call_count == len(Bridge.SYMBOLS)
    assert audit.observational_only is True
    assert audit.readiness.reference_timestamp == NOW
    assert audit.readiness.status == "DATA_READY"
    assert tuple(asset.canonical_symbol for asset in audit.assets) == Bridge.SYMBOLS


def test_policy_is_explicit_and_invalid_policy_fails_before_fetch():
    provider, service = service_for(quotes())
    lifecycle = ExternalObservationalProducerLifecycle(service)

    with pytest.raises((TypeError, ValueError)):
        lifecycle.produce(
            reference_timestamp=NOW.replace(tzinfo=None),
            maximum_staleness_seconds=10,
        )
    assert provider.fetch.call_count == 0

    with pytest.raises((TypeError, ValueError)):
        lifecycle.produce(
            reference_timestamp=NOW,
            maximum_staleness_seconds=-1,
        )
    assert provider.fetch.call_count == 0


def test_symbol_map_is_frozen_before_collection():
    data = quotes()
    mapping = ProviderSymbolMap("fixture")
    for symbol in Bridge.SYMBOLS:
        mapping.set_symbol(symbol, symbol)
    supplied = mapping.snapshot()

    provider = Mock()

    def fetch(symbol):
        # Hostile provider mutates caller-owned mapping during the collection.
        supplied["symbols"][symbol] = "MUTATED"
        return data[symbol]

    provider.fetch.side_effect = fetch
    service = ExternalContextService(
        provider=provider,
        observational_snapshots=True,
    )
    audit = ExternalObservationalProducerLifecycle(service).produce(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
        symbol_map=supplied,
    )

    assert provider.fetch.call_count == len(Bridge.SYMBOLS)
    assert all(asset.provider_identity_verified is True for asset in audit.assets)


def test_failed_collection_cannot_reuse_previous_evidence():
    provider, service = service_for(quotes())
    lifecycle = ExternalObservationalProducerLifecycle(service)
    first = lifecycle.produce(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
    )
    assert first.readiness.status == "DATA_READY"

    provider.fetch.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError):
        lifecycle.produce(
            reference_timestamp=NOW + timedelta(seconds=1),
            maximum_staleness_seconds=10,
        )
    assert service.observational_snapshot() is None


def test_missing_preservation_is_fail_closed_without_second_collection():
    provider = Mock()
    provider.fetch.side_effect = lambda symbol: quotes()[symbol]
    service = ExternalContextService(provider=provider)
    lifecycle = ExternalObservationalProducerLifecycle(service)

    with pytest.raises(ValueError, match="did not preserve"):
        lifecycle.produce(
            reference_timestamp=NOW,
            maximum_staleness_seconds=10,
        )
    assert provider.fetch.call_count == len(Bridge.SYMBOLS)


@pytest.mark.parametrize("bad", [None, object(), Mock()])
def test_invalid_service_rejected(bad):
    with pytest.raises(TypeError):
        ExternalObservationalProducerLifecycle(bad)
