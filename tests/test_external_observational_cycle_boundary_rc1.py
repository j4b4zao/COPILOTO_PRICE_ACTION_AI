"""RC1 acceptance for the explicit external observational cycle boundary."""
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from analysis.research.intermarket_external_context_bridge import (
    IntermarketExternalContextBridge as Bridge,
)
from external_context.external_observational_cycle_boundary import (
    ExternalObservationalCycleBoundary,
    ExternalObservationalCyclePolicy,
)


NOW = datetime(2026, 10, 6, 15, tzinfo=timezone.utc)


def quotes():
    return {
        symbol: {
            "price": 100.0,
            "change": 0.0,
            "timestamp": NOW.isoformat(),
            "provider_symbol": symbol,
            "provider_name": "fixture",
        }
        for symbol in Bridge.SYMBOLS
    }


def provider_for(data=None):
    data = data or quotes()
    provider = Mock()
    provider.fetch.side_effect = lambda symbol: data.get(symbol)
    return provider


def policy(**changes):
    values = {
        "reference_timestamp": NOW,
        "maximum_staleness_seconds": 10,
        "symbol_map": None,
    }
    values.update(changes)
    return ExternalObservationalCyclePolicy(**values)


def test_construction_is_inert_and_requires_explicit_provider():
    provider = provider_for()
    boundary = ExternalObservationalCycleBoundary(provider=provider)

    provider.fetch.assert_not_called()
    assert set(vars(boundary)) == {"_service", "_producer", "_presentation"}

    with pytest.raises(TypeError):
        ExternalObservationalCycleBoundary(provider=object())


def test_policy_requires_explicit_aware_timestamp_and_valid_staleness():
    with pytest.raises((TypeError, ValueError)):
        policy(reference_timestamp=NOW.replace(tzinfo=None))
    with pytest.raises((TypeError, ValueError)):
        policy(maximum_staleness_seconds=-1)


def test_policy_freezes_symbol_map_at_creation():
    supplied = {
        "provider": "fixture",
        "symbols": {symbol: symbol for symbol in Bridge.SYMBOLS},
        "status": {symbol: "MAPPED" for symbol in Bridge.SYMBOLS},
    }
    configured = policy(symbol_map=supplied)
    supplied["symbols"]["US500"] = "MUTATED"

    assert configured.symbol_map["symbols"]["US500"] == "US500"


def test_invalid_symbol_map_contract_fails_before_boundary_collection():
    provider = provider_for()
    boundary = ExternalObservationalCycleBoundary(provider=provider)

    with pytest.raises(TypeError):
        policy(symbol_map={"symbols": [], "status": {}})

    provider.fetch.assert_not_called()


def test_produce_runs_one_explicit_collection_and_returns_completed_audit():
    provider = provider_for()
    boundary = ExternalObservationalCycleBoundary(provider=provider)

    result = boundary.produce(policy())

    assert result.observational_only is True
    assert result.readiness.reference_timestamp == NOW
    assert provider.fetch.call_count == len(Bridge.SYMBOLS)


def test_present_uses_existing_presentation_cycle_and_no_cache():
    provider = provider_for()
    boundary = ExternalObservationalCycleBoundary(provider=provider)
    bot = Mock()
    context = object()

    boundary.present(bot, context, policy())

    assert provider.fetch.call_count == len(Bridge.SYMBOLS)
    bot.mostrar.assert_called_once()
    _, kwargs = bot.mostrar.call_args
    assert kwargs["external_presentation_enabled"] is True
    assert kwargs["external_audit"].observational_only is True


def test_failed_second_collection_does_not_reuse_first_audit():
    provider = provider_for()
    boundary = ExternalObservationalCycleBoundary(provider=provider)
    first = boundary.produce(policy())
    assert first.observational_only is True

    provider.fetch.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError, match="provider failed"):
        boundary.produce(policy())

    assert boundary._service.observational_snapshot() is None


def test_boundary_has_no_default_policy_clock_or_runtime_activation():
    provider = provider_for()
    boundary = ExternalObservationalCycleBoundary(provider=provider)

    with pytest.raises(TypeError):
        boundary.produce(None)
    with pytest.raises(TypeError):
        boundary.present(Mock(), object(), None)

    provider.fetch.assert_not_called()
