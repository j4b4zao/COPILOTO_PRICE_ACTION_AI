"""RC7.2 synthetic causal integration; no strategy performance claims."""
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta

import pytest

from core.analysis_context import AnalysisContext
from models.book_depth import BookLevel
from replay.historical_input_contract import HistoricalDomainObservation, ReplayHistoricalInput
from replay.historical_order_flow import (HistoricalTradeEvent, HistoricalBookSnapshot,
    HistoricalOrderFlowBuilder)
from replay.replay_engine import ReplayEngine, ReplayAbortedError
from tests.test_replay_current_decision_contract_rc1 import OfflinePipeline, bar

T0 = datetime(2026, 10, 7, 10)
SOURCE = "SYNTHETIC_SESSION"


def history(t, available=True, **overrides):
    h = ReplayHistoricalInput.unavailable(t)
    if available:
        h = replace(h, order_flow=HistoricalDomainObservation("ORDER_FLOW", "AVAILABLE", t, SOURCE))
    return replace(h, **overrides)


def flow(t, **changes):
    event = HistoricalTradeEvent(t, t, 100, 2, "BUY", SOURCE, t.isoformat())
    return HistoricalOrderFlowBuilder.build(t, [replace(event, **changes)],
        period_start=t-timedelta(minutes=1), observation_complete=True)


def run(candles, declarations=None, payloads=None, actions=None):
    context = AnalysisContext()
    pipeline = OfflinePipeline(actions or [{} for _ in candles])
    replay = ReplayEngine(pipeline, trusted_offline=True)
    result = replay.executar(context, candles, declarations, historical_order_flow_inputs=payloads)
    return result, context, replay


def assert_operational_equal(a, b):
    for f in fields(a):
        if f.name != "audit":
            assert getattr(a, f.name) == getattr(b, f.name)
    assert replace(a.audit, historical_order_flow=()) == replace(b.audit, historical_order_flow=())


def test_optional_legacy_and_explicit_unavailable_match():
    a, ca, _ = run([bar(0)])
    b, cb, _ = run([bar(0)], [history(T0, False)])
    assert a == b
    assert a.audit.historical_order_flow[0].status == "UNAVAILABLE"
    assert ca.order_flow_state is cb.order_flow_state is None


@pytest.mark.parametrize("action", ["BUY", "SELL", "WAIT"])
def test_no_operational_influence_for_all_decisions(action):
    a, ca, _ = run([bar(0)], actions=[{"action": action}])
    b, cb, _ = run([bar(0)], [history(T0)], [flow(T0)], [{"action": action}])
    assert_operational_equal(a, b)
    for f in fields(ca):
        if f.name not in ("market", "economic_calendar"):
            assert getattr(ca, f.name) == getattr(cb, f.name)
    assert ca.market.candles.all() == cb.market.candles.all()
    assert cb.order_flow_state is None and not cb.book_depth.available
    assert b.audit.historical_order_flow[0].delta == 2


def test_official_pipeline_results_are_equivalent():
    from analysis.analysis_pipeline import AnalysisPipeline
    a = ReplayEngine(AnalysisPipeline()).executar(AnalysisContext(), [bar(0)])
    b = ReplayEngine(AnalysisPipeline()).executar(AnalysisContext(), [bar(0)], [history(T0)],
        historical_order_flow_inputs=[flow(T0)])
    assert_operational_equal(a, b)


def test_authorized_snapshot_is_frozen_and_input_unchanged():
    payload = flow(T0)
    result, _, _ = run([bar(0)], [history(T0)], [payload])
    snapshot = result.audit.historical_order_flow[0]
    assert snapshot == payload
    with pytest.raises(FrozenInstanceError):
        snapshot.trades[0].quantity = 99
    assert payload.delta == 2


@pytest.mark.parametrize("domain", ["external", "economic_calendar", "book_depth"])
def test_unsupported_available_domains_rejected(domain):
    h = history(T0, False, **{domain: HistoricalDomainObservation(domain.upper(), "AVAILABLE", T0, SOURCE)})
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [h])
    assert "UNSUPPORTED_HISTORICAL_DOMAIN" in str(e.value.__cause__)
    assert e.value.audit_snapshot.abort_stage == "HISTORICAL_INPUT"
    assert e.value.audit_snapshot.candles_processed == 0


@pytest.mark.parametrize("payloads", [None, [None], [object()]])
def test_available_requires_explicit_payload(payloads):
    with pytest.raises(ReplayAbortedError, match="HISTORICAL_INPUT"):
        run([bar(0)], [history(T0)], payloads)


def test_payload_without_rc5_authorization_rejected():
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], None, [flow(T0)])
    assert "WITHOUT_AUTHORIZATION" in str(e.value.__cause__)


@pytest.mark.parametrize("changes", [dict(source_id=""), dict(source_id="OTHER"), dict(event_id=None)])
def test_provenance_and_identity_validation(changes):
    with pytest.raises(ReplayAbortedError):
        run([bar(0)], [history(T0)], [flow(T0, **changes)])


def test_future_payload_cutoff_rejected():
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [history(T0)], [flow(T0+timedelta(seconds=1))])
    assert "TIMESTAMP_MISMATCH" in str(e.value.__cause__)


def test_revalidates_future_events_even_if_payload_was_tampered():
    payload = flow(T0)
    object.__setattr__(payload.trades[0], "observed_at", T0+timedelta(seconds=1))
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [history(T0)], [payload])
    assert "FUTURE_EVENT" in str(e.value.__cause__)


def test_envelope_cannot_predate_event_observation():
    h = history(T0, order_flow=HistoricalDomainObservation("ORDER_FLOW", "AVAILABLE",
        T0-timedelta(seconds=1), SOURCE))
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [h], [flow(T0)])
    assert "ENVELOPE_PRECEDES_EVIDENCE" in str(e.value.__cause__)


def test_dedup_is_preserved():
    s = flow(T0)
    object.__setattr__(s, "trades", s.trades*2)
    result, _, _ = run([bar(0)], [history(T0)], [s])
    assert result.audit.historical_order_flow[0].total_quantity == 2


def test_unknown_is_not_inferred():
    result, _, _ = run([bar(0)], [history(T0)], [flow(T0, aggressor="UNKNOWN")])
    assert result.audit.historical_order_flow[0].delta is None


def test_gap_has_no_carry_forward_and_recovery_is_new_window():
    candles = [bar(i) for i in range(3)]
    hs = [history(c.timestamp, i!=1) for i,c in enumerate(candles)]
    result, _, _ = run(candles, hs, [flow(candles[0].timestamp), None, flow(candles[2].timestamp)])
    snapshots = result.audit.historical_order_flow
    assert [s.status for s in snapshots] == ["AVAILABLE", "UNAVAILABLE", "AVAILABLE"]
    assert snapshots[1].trades == () and snapshots[1].book is None
    assert snapshots[2].total_quantity == 2


def test_overlapping_period_after_gap_rejected_with_certified_prefix():
    candles = [bar(i) for i in range(3)]
    payload = replace(flow(candles[2].timestamp), period_start=T0-timedelta(minutes=1))
    with pytest.raises(ReplayAbortedError) as e:
        run(candles, [history(T0), history(candles[1].timestamp, False), history(candles[2].timestamp)],
            [flow(T0), None, payload])
    assert "OVERLAPPING_PERIOD" in str(e.value.__cause__)
    assert len(e.value.audit_snapshot.historical_order_flow) == 2


def test_reused_event_id_across_windows_is_rejected():
    candles = [bar(0), bar(1)]
    with pytest.raises(ReplayAbortedError) as e:
        run(candles, [history(c.timestamp) for c in candles],
            [flow(T0, event_id="same"), flow(candles[1].timestamp, event_id="same")])
    assert "EVENT_REUSED" in str(e.value.__cause__)


@pytest.mark.parametrize("payloads", [[], [flow(T0), None]])
def test_sequence_length_must_match(payloads):
    with pytest.raises(ReplayAbortedError):
        run([bar(0)], [history(T0)], payloads)


def test_sessions_and_repeated_sequences_are_isolated():
    replay = ReplayEngine(OfflinePipeline([{}]), trusted_offline=True)
    a = replay.executar(AnalysisContext(), [bar(0)], [history(T0)], historical_order_flow_inputs=[flow(T0)])
    b = replay.executar(AnalysisContext(), [bar(0)], [history(T0)], historical_order_flow_inputs=[flow(T0)])
    assert a == b
    c = replay.executar(AnalysisContext(), [bar(0)])
    assert not c.audit.historical_order_flow[0].available


def test_prefix_snapshots_unchanged_by_future_candles():
    candles = [bar(0), bar(1)]
    hs = [history(c.timestamp) for c in candles]
    ss = [flow(c.timestamp) for c in candles]
    prefix, _, _ = run(candles[:1], hs[:1], ss[:1])
    full, _, _ = run(candles, hs, ss)
    assert prefix.audit.historical_order_flow == full.audit.historical_order_flow[:1]


def test_current_book_cannot_bypass_unsupported_domain_gate():
    b = HistoricalBookSnapshot(T0, SOURCE, (BookLevel(99,1),), (BookLevel(101,1),), True, True)
    payload = replace(flow(T0), book=b)
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [history(T0)], [payload])
    assert "UNSUPPORTED_HISTORICAL_DOMAIN:BOOK_DEPTH" in str(e.value.__cause__)


def test_stale_book_not_promoted_into_audit():
    b = HistoricalBookSnapshot(T0-timedelta(seconds=1), SOURCE,
        (BookLevel(99,1),), (BookLevel(101,1),), True, True)
    payload = replace(flow(T0), book=b)
    result, _, _ = run([bar(0)], [history(T0)], [payload])
    assert result.audit.historical_order_flow[0].book is None


def test_session_provenance_cannot_switch_mid_replay():
    candles = [bar(0), bar(1)]
    h = history(candles[1].timestamp, order_flow=HistoricalDomainObservation(
        "ORDER_FLOW", "AVAILABLE", candles[1].timestamp, "ANOTHER_SYNTHETIC_SESSION"))
    with pytest.raises(ReplayAbortedError) as e:
        run(candles, [history(T0), h], [flow(T0),
            flow(candles[1].timestamp, source_id="ANOTHER_SYNTHETIC_SESSION")])
    assert "SESSION_PROVENANCE_CHANGED" in str(e.value.__cause__)


def test_future_rc5_observation_revalidated_at_consumption():
    h = history(T0)
    object.__setattr__(h.order_flow, "observed_at", T0+timedelta(seconds=1))
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [h], [flow(T0)])
    assert e.value.audit_snapshot.candles_processed == 0


def test_prefix_failure_does_not_publish_unprocessed_snapshot():
    class FailingPipeline:
        def executar(self, context):
            raise RuntimeError("SYNTHETIC_FAILURE")
    replay = ReplayEngine(FailingPipeline(), trusted_offline=True)
    with pytest.raises(ReplayAbortedError) as e:
        replay.executar(AnalysisContext(), [bar(0)], [history(T0)],
            historical_order_flow_inputs=[flow(T0)])
    assert e.value.audit_snapshot.historical_order_flow == ()


def test_source_case_alias_cannot_double_count_same_event():
    s = flow(T0)
    object.__setattr__(s, "trades", (s.trades[0], replace(s.trades[0], source_id=SOURCE.lower())))
    result, _, _ = run([bar(0)], [history(T0)], [s])
    snapshot = result.audit.historical_order_flow[0]
    assert snapshot.available and len(snapshot.trades) == 1
    assert snapshot.total_quantity == snapshot.delta == 2


def test_integration_canonical_alias_conflict_aborts_explicitly():
    s = flow(T0)
    object.__setattr__(s, "trades", (s.trades[0], replace(s.trades[0],
        source_id=SOURCE.lower(), quantity=3)))
    with pytest.raises(ReplayAbortedError) as e:
        run([bar(0)], [history(T0)], [s])
    assert "CONFLICTING_EVENT_ID" in str(e.value.__cause__)


def test_integration_distinct_ids_keep_volume_and_delta():
    s = flow(T0)
    object.__setattr__(s, "trades", (s.trades[0], replace(s.trades[0],
        source_id=SOURCE.lower(), event_id="different")))
    result, _, _ = run([bar(0)], [history(T0)], [s])
    assert len(result.audit.historical_order_flow[0].trades) == 2
    assert result.audit.historical_order_flow[0].total_quantity == 4
    assert result.audit.historical_order_flow[0].delta == 4
