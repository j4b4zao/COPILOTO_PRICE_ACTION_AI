"""RC3 opening evidence, causal input boundary and fault-stage integration."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta
import pickle
from unittest.mock import patch

import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from economic_context.economic_calendar_state import EconomicCalendarState
from models.candle import Candle
from performance.order_flow_experiment_metrics import OrderFlowExperimentMetrics
from replay.replay_engine import ReplayAbortedError, ReplayEngine
from replay.replay_statistics import ReplayStatistics
from replay.trade_simulator import TradeSimulator

T0 = datetime(2026, 10, 7, 10)


def bar(index=0, **values):
    defaults = dict(open=100, high=101, low=99, close=100, volume=10,
                    timestamp=T0 + timedelta(minutes=index))
    defaults.update(values)
    return Candle(**defaults)


class Pipeline:
    def __init__(self, samples):
        self.samples = samples
        self.index = 0

    def executar(self, context):
        sample = self.samples[self.index]
        self.index += 1
        if sample.get("exception"):
            raise RuntimeError("pipeline diagnostic")
        context.clear_results()
        decision, risk = context.decision, context.risk
        action = sample.get("action", "WAIT")
        decision.action = action
        decision.direction = decision.signal = action if action in ("BUY", "SELL") else "NONE"
        decision.valid = sample.get("valid", action in ("BUY", "SELL"))
        decision.setup = sample.get("setup", "ENTRY")
        decision.entry = risk.entry_price = sample.get("entry", context.market.last_price)
        decision.stop = risk.stop_loss = 93 if action == "BUY" else 107
        decision.target = risk.take_profit = 119 if action == "BUY" else 81
        decision.risk_reward = risk.risk_reward = 19 / 7
        risk.valid = risk.approved = sample.get("risk", True)
        if sample.get("bad_direction"):
            decision.direction = "SELL"
        if sample.get("missing_decision"):
            context.decision = None


def replay(samples):
    return ReplayEngine(Pipeline(samples), trusted_offline=True)


def run(samples, candles=None):
    return replay(samples).executar(AnalysisContext(), [bar(i) for i in range(len(samples))] if candles is None else candles)


def invariants(audit):
    assert audit.candles_processed == (audit.trades_opened + audit.skipped + audit.rejected + audit.unresolved_candles)
    assert 0 <= audit.trades_closed <= audit.trades_opened <= audit.decision_buy_sell <= audit.candles_processed
    assert audit.trades_opened - audit.trades_closed in (0, 1)
    assert audit.unresolved_candles in (0, 1)
    assert len(audit.closed_trades) == audit.trades_closed
    assert audit.statistics_committed_trades <= audit.trades_closed
    assert sum(n for category, _, n in audit.reason_counts if category == "EXPECTED_SKIP") == audit.skipped
    assert sum(n for category, _, n in audit.reason_counts if category != "EXPECTED_SKIP") == audit.rejected
    if audit.completed:
        assert not audit.aborted
        assert audit.unresolved_candles == 0
        assert audit.trades_opened == audit.trades_closed
        assert audit.pending_open_trade is None


def test_empty_session_completed():
    result = run([])
    invariants(result.audit)
    assert result.audit.completed and not result.audit.aborted
    assert result.audit.reason_counts == result.audit.closed_trades == ()
    assert result.audit.candles_processed == result.operations == 0


def test_wait_is_skip_and_typed_incoherent_wait_is_rejection():
    result = run([{}, {"bad_direction": True}])
    assert (result.audit.skipped, result.audit.rejected) == (1, 1)
    assert result.audit.reason_counts == (("CONTRACT_REJECTION", "DECISION_NOT_AUTHORIZED", 1),
                                           ("EXPECTED_SKIP", "DECISION_NOT_AUTHORIZED", 1))
    invariants(result.audit)


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_authorized_open_and_session_end(direction):
    result = run([{"action": direction}])
    a = result.audit
    assert (a.decision_buy_sell, a.trades_opened, a.trades_closed, a.statistics_committed_trades) == (1, 1, 1, 1)
    assert a.closed_trades[0].reason == "SESSION_END"
    assert a.closed_trades[0].profit == 0
    assert result.wins == 1  # Deliberately retain the RC1 zero-profit convention.
    invariants(a)


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_risk_rejection(direction):
    result = run([{"action": direction, "risk": False}])
    assert result.audit.reason_counts == (("CONTRACT_REJECTION", "RISK_NOT_APPROVED", 1),)
    assert result.audit.decision_buy_sell == 1
    invariants(result.audit)


def test_invalid_contract_and_unsupported_entry():
    result = run([{"action": "BUY", "valid": False}, {"action": "BUY", "entry": 100.1}])
    assert result.audit.reason_counts == (("CONTRACT_REJECTION", "DECISION_NOT_AUTHORIZED", 1),
                                           ("CONTRACT_REJECTION", "UNSUPPORTED_ENTRY_MODEL", 1))
    invariants(result.audit)


def test_position_already_open_wait_and_buy_classification():
    result = run([{"action": "BUY"}, {}, {"action": "SELL"}])
    assert result.audit.reason_counts == (("EXPECTED_SKIP", "POSITION_ALREADY_OPEN", 1),
                                           ("STATE_REJECTION", "POSITION_ALREADY_OPEN", 1))
    assert (result.audit.trades_opened, result.audit.skipped, result.audit.rejected) == (1, 1, 1)
    invariants(result.audit)


def test_loss_is_not_rejection_and_original_setup_kept():
    result = run([{"action": "BUY", "setup": "FIRST"}, {"setup": "LATER"}], [bar(), bar(1, low=92)])
    assert result.losses == 1
    assert result.audit.rejected == 0
    assert result.audit.closed_trades[0].profit == -7
    assert result.audit.closed_trades[0].setup == "FIRST"
    assert set(result.setups) == {"FIRST"}
    invariants(result.audit)


def test_frozen_audit_closed_trade_and_independent_results():
    engine = replay([{"action": "BUY"}])
    first = engine.executar(AnalysisContext(), [bar()])
    before = pickle.dumps(first)
    with pytest.raises(FrozenInstanceError):
        first.audit.rejected = 99
    with pytest.raises(FrozenInstanceError):
        first.audit.closed_trades[0].entry = 999
    second = engine.executar(AnalysisContext(), [bar()])
    assert first.audit == second.audit
    second.setups["ENTRY"]["wins"] = 999
    assert pickle.dumps(first) == before


def test_closed_snapshot_is_not_trade_reference():
    captured = []
    original = TradeSimulator.close
    def close(simulator, price, **kwargs):
        trade = original(simulator, price, **kwargs)
        captured.append(trade)
        return trade
    with patch.object(TradeSimulator, "close", close):
        result = run([{"action": "BUY"}])
    captured[0].entry = 999
    captured[0].setup = "MUTATED"
    assert result.audit.closed_trades[0].entry == 100
    assert result.audit.closed_trades[0].setup == "ENTRY"


def test_custom_pipeline_gate_before_dangerous_copy():
    called = []
    class Dangerous(Pipeline):
        def __deepcopy__(self, memo):
            called.append(True)
            raise AssertionError("must not copy")
    with pytest.raises(ValueError):
        ReplayEngine(Dangerous([])).executar(AnalysisContext(), [])
    assert not called


def test_custom_trusted_scope_and_official_scope():
    assert run([]).audit.offline_scope == "CALLER_DECLARED"
    result = ReplayEngine(AnalysisPipeline()).executar(AnalysisContext(), [])
    assert result.audit.offline_scope == "KNOWN_OFFLINE_CONTRACT"


@pytest.mark.parametrize("name", ReplayEngine._LIVE_RESOURCES)
def test_known_resource_rejected_before_copy_and_consumption(name):
    pipeline = Pipeline([])
    setattr(pipeline, name, object())
    called = []
    with patch.object(Pipeline, "__deepcopy__", lambda *args: called.append(True), create=True):
        with pytest.raises(ValueError):
            ReplayEngine(pipeline, trusted_offline=True).executar(AnalysisContext(), iter(()))
    assert not called


@pytest.mark.parametrize("name", ["multi_timeframe", "order_flow_state", "external_market", "economic_calendar",
                                  "decision", "risk", "strategy", "score", "book_depth", "market"])
def test_contaminated_context_fails_before_copy(name):
    context = AnalysisContext()
    if name in ("multi_timeframe", "order_flow_state"):
        setattr(context, name, object())
    elif name == "external_market":
        context.external_market.valid = True
    elif name == "economic_calendar":
        context.economic_calendar = replace(context.economic_calendar, source="HISTORICAL")
    elif name == "book_depth":
        context.book_depth = replace(context.book_depth, available=True)
    elif name == "market":
        context.market.last_price = 100
    else:
        getattr(context, name).valid = True
    before = pickle.dumps(context)
    with patch("replay.replay_engine.deepcopy", side_effect=AssertionError("must not copy")):
        with pytest.raises(ValueError):
            replay([]).executar(context, [])
    assert pickle.dumps(context) == before


def test_calendar_construction_timestamp_is_not_contamination():
    context = AnalysisContext()
    context.economic_calendar = EconomicCalendarState.unavailable(observed_at=T0)
    assert replay([]).executar(context, []).audit.completed


def assert_abort(engine, candles, stage, *, context=None):
    with pytest.raises(ReplayAbortedError) as caught:
        engine.executar(AnalysisContext() if context is None else context, candles)
    error = caught.value
    assert error.audit_snapshot.aborted and not error.audit_snapshot.completed
    assert error.audit_snapshot.abort_stage == stage
    assert error.__cause__ is not None
    assert error.result_snapshot.audit is error.audit_snapshot
    invariants(error.audit_snapshot)
    return error


@pytest.mark.parametrize("invalid,reason", [(bar(timestamp=None), "INVALID_CANDLE"),
                                           (bar(high=98), "INVALID_CANDLE"),
                                           (bar(close=float("nan")), "INVALID_CANDLE")])
def test_invalid_candle_aborts(invalid, reason):
    error = assert_abort(replay([]), [invalid], "VALIDATE")
    assert error.audit_snapshot.candles_processed == 0
    assert error.audit_snapshot.abort_candle_index == 0
    assert error.audit_snapshot.abort_reason == reason


@pytest.mark.parametrize("index", [0, -1])
def test_duplicate_out_of_order_preserve_prefix(index):
    error = assert_abort(replay([{}]), [bar(), bar(index)], "VALIDATE")
    assert error.audit_snapshot.candles_processed == error.audit_snapshot.skipped == 1
    assert error.audit_snapshot.abort_candle_index == 1
    assert error.audit_snapshot.abort_reason == "NON_INCREASING_TIMESTAMP"


def test_pipeline_abort_with_open_trade_keeps_pending_no_fake_close():
    engine = replay([{"action": "BUY"}, {"exception": True}])
    error = assert_abort(engine, [bar(), bar(1)], "PIPELINE")
    a = error.audit_snapshot
    assert (a.trades_opened, a.trades_closed, a.unresolved_candles) == (1, 0, 1)
    assert a.pending_open_trade.entry == 100
    assert a.pending_open_trade.last_timestamp == bar(1).timestamp
    assert engine.simulator.opened
    assert error.result_snapshot.operations == 0
    assert type(error.__cause__) is RuntimeError


def test_missing_decision_aborts_open_without_fabricated_rejection():
    error = assert_abort(replay([{"missing_decision": True}]), [bar()], "OPEN")
    assert error.audit_snapshot.rejected == 0
    assert error.audit_snapshot.unresolved_candles == 1
    assert type(error.__cause__) is AttributeError


@pytest.mark.parametrize("owner,method,stage,samples,candles", [
    (MarketState, "update", "MARKET", [{}], [bar()]),
    (TradeSimulator, "update", "UPDATE", [{}], [bar()]),
    (TradeSimulator, "simulate", "OPEN", [{"action": "BUY"}], [bar()]),
    (OrderFlowExperimentMetrics, "register", "METRICS", [{}], [bar()]),
    (ReplayStatistics, "finish", "FINISH", [{}], [bar()]),
    (ReplayEngine, "_snapshot_result", "SNAPSHOT", [{}], [bar()]),
    (TradeSimulator, "close", "SESSION_END_CLOSE", [{"action": "BUY"}], [bar()]),
])
def test_fault_stage_does_not_retry(owner, method, stage, samples, candles):
    original_error = RuntimeError("unstable diagnostic excluded from canonical code")
    with patch.object(owner, method, side_effect=original_error) as fault:
        error = assert_abort(replay(samples), candles, stage)
        assert error.__cause__ is original_error
        assert fault.call_count == 1
        assert error.audit_snapshot.abort_reason == stage + "_ERROR"


@pytest.mark.parametrize("session_end", [False, True])
def test_register_failure_records_closure_before_statistics_and_does_not_retry(session_end):
    samples = [{"action": "BUY"}] if session_end else [{"action": "BUY"}, {}]
    candles = [bar()] if session_end else [bar(), bar(1, high=120)]
    stage = "SESSION_END_REGISTER" if session_end else "REGISTER"
    original = ReplayStatistics.register_operation
    def partial_failure(statistics, strategy, profit):
        original(statistics, strategy, profit)
        raise RuntimeError("failure after mutation")
    with patch.object(ReplayStatistics, "register_operation", side_effect=partial_failure, autospec=True) as fault:
        error = assert_abort(replay(samples), candles, stage)
        assert fault.call_count == 1
    assert error.audit_snapshot.trades_closed == 1
    assert error.audit_snapshot.statistics_committed_trades == 0
    assert error.result_snapshot.operations == 0
    assert error.audit_snapshot.pending_open_trade is None


def test_metrics_snapshot_failure_does_not_retry_snapshot():
    with patch.object(OrderFlowExperimentMetrics, "snapshot", side_effect=RuntimeError("snapshot")) as fault:
        assert_abort(replay([{}]), [bar()], "METRICS")
        assert fault.call_count == 1


def test_iterator_failure_keeps_prefix():
    def broken():
        yield bar()
        raise RuntimeError("iterator")
    error = assert_abort(replay([{}]), broken(), "ITERATE")
    assert error.audit_snapshot.skipped == error.audit_snapshot.candles_processed == 1
    assert error.audit_snapshot.abort_candle_index == 1
    assert error.audit_snapshot.abort_timestamp is None


def test_initial_iterator_failure_is_session_abort():
    class BadIterable:
        def __iter__(self):
            raise RuntimeError("iter")
    error = assert_abort(replay([]), BadIterable(), "ITERATE")
    assert error.audit_snapshot.candles_processed == 0


def test_input_candle_copied_before_ingestion_and_opening_range_not_used():
    source = bar(high=125, low=85)
    engine = replay([{"action": "BUY"}])
    context = AnalysisContext()
    def stream():
        yield source
        assert engine.simulator.opened
        source.close = 999
        source.high = 999
        assert context.market.last_candle.close == 100
    result = engine.executar(context, stream())
    assert result.audit.closed_trades[0].reason == "SESSION_END"
    assert result.audit.closed_trades[0].exit == 100
    assert result.audit.closed_trades[0].profit == 0


def test_audit_consumer_does_not_mutate_decision_or_risk():
    original = TradeSimulator.simulate
    seen = []
    def checked(simulator, context, candle):
        before = pickle.dumps((context.decision, context.risk, context.strategy, context.score, context.alert))
        trade = original(simulator, context, candle)
        assert pickle.dumps((context.decision, context.risk, context.strategy, context.score, context.alert)) == before
        seen.append(True)
        return trade
    with patch.object(TradeSimulator, "simulate", checked):
        result = run([{"action": "BUY"}, {}])
    assert len(seen) == 2
    invariants(result.audit)


@pytest.mark.parametrize("error_type", [KeyboardInterrupt, SystemExit, MemoryError])
def test_control_or_fatal_exception_not_wrapped(error_type):
    with patch.object(TradeSimulator, "simulate", side_effect=error_type):
        with pytest.raises(error_type):
            run([{"action": "BUY"}])


def test_metrics_clear_failure_is_preflight_not_session_abort():
    # Create metrics/engine before fault so only executar's clear fails.
    engine = replay([])
    with patch.object(OrderFlowExperimentMetrics, "clear", side_effect=RuntimeError("clear")):
        with pytest.raises(RuntimeError) as error:
            engine.executar(AnalysisContext(), [])
    assert not isinstance(error.value, ReplayAbortedError)


def test_mutable_trade_metadata_cannot_enter_frozen_snapshot():
    original = TradeSimulator.simulate
    def corrupt(simulator, context, candle):
        trade = original(simulator, context, candle)
        trade.setup = []
        return trade
    with patch.object(TradeSimulator, "simulate", corrupt):
        error = assert_abort(replay([{"action": "BUY"}]), [bar()], "OPEN")
    assert error.audit_snapshot.uncertain_state
    assert type(error.__cause__) is TypeError


def test_readable_buy_counter_is_observation_not_type_authorization():
    from types import SimpleNamespace
    original = Pipeline.executar
    def malformed(pipeline, context):
        original(pipeline, context)
        context.decision = SimpleNamespace(action="BUY", valid=False)
    with patch.object(Pipeline, "executar", malformed):
        result = run([{}])
    assert result.audit.decision_buy_sell == 1
    assert result.audit.trades_opened == 0
    assert result.audit.rejected == 1
    invariants(result.audit)


def test_market_mutation_then_failure_marks_uncertain_without_fake_admission():
    original = MarketState.update
    def failed(market, **kwargs):
        original(market, **kwargs)
        raise RuntimeError("partial market mutation")
    with patch.object(MarketState, "update", failed):
        error = assert_abort(replay([{}]), [bar()], "MARKET")
    assert error.audit_snapshot.uncertain_state
    assert error.audit_snapshot.candles_processed == 0


def test_simulator_partial_mutation_preserves_last_certified_pending_snapshot():
    original = TradeSimulator.update
    def failed(simulator, candle):
        if simulator.opened:
            simulator.trade.bars += 10
            raise RuntimeError("partial position mutation")
        return original(simulator, candle)
    with patch.object(TradeSimulator, "update", failed):
        error = assert_abort(replay([{"action": "BUY"}, {}]), [bar(), bar(1)], "UPDATE")
    assert error.audit_snapshot.uncertain_state
    assert error.audit_snapshot.pending_open_trade.bars == 0
    assert error.audit_snapshot.trades_closed == 0


def test_unknown_official_engine_rejected_before_deepcopy():
    pipeline = AnalysisPipeline()
    pipeline.engines[0] = object()
    with patch("replay.replay_engine.deepcopy", side_effect=AssertionError("must not copy")):
        with pytest.raises(ValueError):
            ReplayEngine(pipeline).executar(AnalysisContext(), [])
