"""RC1 acceptance for explicit manual external-cycle activation."""
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
from external_context.external_observational_manual_activation import (
    ExternalObservationalManualActivation,
)


NOW = datetime(2026, 10, 6, 15, tzinfo=timezone.utc)


def configured():
    payloads = {
        symbol: {
            "price": 100.0,
            "change": 0.0,
            "timestamp": NOW.isoformat(),
            "provider_symbol": symbol,
            "provider_name": "fixture",
        }
        for symbol in Bridge.SYMBOLS
    }
    provider = Mock()
    provider.fetch.side_effect = lambda symbol: payloads.get(symbol)
    boundary = ExternalObservationalCycleBoundary(provider=provider)
    activation = ExternalObservationalManualActivation(boundary)
    policy = ExternalObservationalCyclePolicy(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
    )
    return provider, boundary, activation, policy


def test_requires_configured_boundary():
    for bad in (None, object(), Mock()):
        with pytest.raises(TypeError):
            ExternalObservationalManualActivation(bad)


def test_default_disabled_never_collects():
    provider, _, activation, policy = configured()

    with pytest.raises(PermissionError, match="disabled"):
        activation.produce(policy)

    provider.fetch.assert_not_called()


def test_explicit_false_never_collects_or_presents():
    provider, _, activation, policy = configured()
    bot = Mock()

    with pytest.raises(PermissionError):
        activation.present(bot, object(), policy, enabled=False)

    provider.fetch.assert_not_called()
    bot.mostrar.assert_not_called()


@pytest.mark.parametrize("bad", [1, 0, "true", None, object()])
def test_non_bool_activation_values_fail_closed_before_collection(bad):
    provider, _, activation, policy = configured()

    with pytest.raises(TypeError):
        activation.produce(policy, enabled=bad)

    provider.fetch.assert_not_called()


def test_enabled_produce_runs_exactly_one_boundary_cycle():
    provider, _, activation, policy = configured()

    result = activation.produce(policy, enabled=True)

    assert result.observational_only is True
    assert result.readiness.reference_timestamp == NOW
    assert provider.fetch.call_count == len(Bridge.SYMBOLS)


def test_enabled_present_reaches_existing_bot_seam_once():
    provider, _, activation, policy = configured()
    bot = Mock()
    context = object()

    result = activation.present(bot, context, policy, enabled=True)

    assert result is bot.mostrar.return_value
    assert provider.fetch.call_count == len(Bridge.SYMBOLS)
    bot.mostrar.assert_called_once()
    args, kwargs = bot.mostrar.call_args
    assert args == (context,)
    assert kwargs["external_presentation_enabled"] is True
    assert kwargs["external_audit"].observational_only is True


def test_invalid_policy_fails_before_collection_when_enabled():
    provider, _, activation, _ = configured()

    with pytest.raises(TypeError):
        activation.produce(None, enabled=True)

    provider.fetch.assert_not_called()


def test_invalid_bot_fails_before_collection_when_enabled():
    provider, _, activation, policy = configured()

    with pytest.raises(TypeError):
        activation.present(object(), object(), policy, enabled=True)

    provider.fetch.assert_not_called()


def test_failed_collection_does_not_present_or_cache_previous_audit():
    provider, _, activation, policy = configured()
    bot = Mock()

    activation.present(bot, object(), policy, enabled=True)
    assert bot.mostrar.call_count == 1

    provider.fetch.side_effect = RuntimeError("provider failed")
    with pytest.raises(RuntimeError, match="provider failed"):
        activation.present(bot, object(), policy, enabled=True)

    assert bot.mostrar.call_count == 1
    assert set(vars(activation)) == {"_boundary"}


def test_activation_has_no_clock_provider_policy_or_bot_ownership():
    provider, boundary, activation, _ = configured()

    assert vars(activation) == {"_boundary": boundary}
    provider.fetch.assert_not_called()
