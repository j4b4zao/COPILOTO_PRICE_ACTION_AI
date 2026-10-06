"""RC1 explicit producer-to-presentation cycle acceptance tests."""
from dataclasses import replace
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from analysis.research.intermarket_external_context_bridge import ExternalBridgeAudit
from external_context.external_observational_presentation_cycle import (
    ExternalObservationalPresentationCycle,
)
from tests.test_intermarket_external_context_bridge_rc1 import audit, snapshots


NOW = datetime(2026, 10, 6, 15, tzinfo=timezone.utc)


def completed_audit():
    return audit(snapshots())


def test_constructor_requires_explicit_producer():
    for bad in (None, object()):
        with pytest.raises(TypeError):
            ExternalObservationalPresentationCycle(bad)


def test_produce_for_presentation_forwards_explicit_policy_once():
    supplied = completed_audit()
    producer = Mock()
    producer.produce.return_value = supplied
    cycle = ExternalObservationalPresentationCycle(producer)
    symbol_map = {"provider": "fixture", "symbols": {}, "status": {}}

    result = cycle.produce_for_presentation(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
        symbol_map=symbol_map,
    )

    assert result is supplied
    producer.produce.assert_called_once_with(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
        symbol_map=symbol_map,
    )
    assert vars(cycle) == {"_producer": producer}


@pytest.mark.parametrize("bad", [None, object(), {}, []])
def test_invalid_producer_result_fails_closed(bad):
    producer = Mock()
    producer.produce.return_value = bad
    cycle = ExternalObservationalPresentationCycle(producer)

    with pytest.raises(TypeError):
        cycle.produce_for_presentation(
            reference_timestamp=NOW,
            maximum_staleness_seconds=10,
        )


def test_non_observational_result_is_rejected():
    producer = Mock()
    producer.produce.return_value = replace(completed_audit(), observational_only=False)
    cycle = ExternalObservationalPresentationCycle(producer)

    with pytest.raises(ValueError, match="observational-only"):
        cycle.produce_for_presentation(
            reference_timestamp=NOW,
            maximum_staleness_seconds=10,
        )


def test_present_passes_only_completed_audit_to_existing_bot_seam():
    supplied = completed_audit()
    producer = Mock()
    producer.produce.return_value = supplied
    bot = Mock()
    context = object()
    cycle = ExternalObservationalPresentationCycle(producer)

    result = cycle.present(
        bot,
        context,
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
    )

    assert result is bot.mostrar.return_value
    producer.produce.assert_called_once()
    bot.mostrar.assert_called_once_with(
        context,
        external_audit=supplied,
        external_presentation_enabled=True,
    )


def test_present_validates_bot_before_collecting():
    producer = Mock()
    cycle = ExternalObservationalPresentationCycle(producer)

    with pytest.raises(TypeError):
        cycle.present(
            object(),
            object(),
            reference_timestamp=NOW,
            maximum_staleness_seconds=10,
        )

    producer.produce.assert_not_called()


def test_producer_failure_never_calls_bot_or_reuses_previous_audit():
    first = completed_audit()
    producer = Mock()
    producer.produce.side_effect = [first, RuntimeError("provider failed")]
    bot = Mock()
    cycle = ExternalObservationalPresentationCycle(producer)

    cycle.present(
        bot,
        object(),
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
    )
    assert bot.mostrar.call_count == 1

    with pytest.raises(RuntimeError, match="provider failed"):
        cycle.present(
            bot,
            object(),
            reference_timestamp=NOW,
            maximum_staleness_seconds=10,
        )

    assert bot.mostrar.call_count == 1
    assert vars(cycle) == {"_producer": producer}


def test_adapter_has_no_clock_cache_or_runtime_bootstrap_dependencies():
    producer = Mock()
    producer.produce.return_value = completed_audit()
    cycle = ExternalObservationalPresentationCycle(producer)

    result = cycle.produce_for_presentation(
        reference_timestamp=NOW,
        maximum_staleness_seconds=10,
    )

    assert isinstance(result, ExternalBridgeAudit)
    assert set(vars(cycle)) == {"_producer"}
