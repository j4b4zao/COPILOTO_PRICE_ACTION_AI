"""Lifecycle integration tests with an isolated, deterministic offline pipeline."""
import copy
import pickle
from datetime import datetime, timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core.analysis_context import AnalysisContext
from models.candle import Candle
from performance.order_flow_experiment_metrics import OrderFlowExperimentMetrics
from replay.replay_engine import ReplayEngine


T0 = datetime(2026, 10, 7, 10)


def bar(minute, **values):
    data = dict(open=100, high=101, low=99, close=100, volume=100,
                timestamp=T0 + timedelta(minutes=minute))
    data.update(values)
    return Candle(**data)


class OfflinePipeline:
    def __init__(self, samples):
        self.samples = samples
        self.index = 0

    def executar(self, context):
        sample = self.samples[self.index]
        self.index += 1
        # Verifies pipeline consumes the ingested current candle.
        assert context.market.last_price == sample.get("close", 100)
        context.clear_results()
        context.strategy.valid = sample.get("strategy_valid", True)
        context.strategy.signal = sample.get("action", "BUY")
        context.strategy.name = sample.get("setup", "CURRENT")
        decision, risk = context.decision, context.risk
        action = sample.get("action", "WAIT")
        decision.valid = sample.get("valid", True)
        decision.action = decision.direction = decision.signal = action
        decision.setup = sample.get("setup", "ORIGINAL")
        decision.entry = risk.entry_price = sample.get("entry", context.market.last_price)
        decision.stop = risk.stop_loss = 93 if action == "BUY" else 107
        decision.target = risk.take_profit = 119 if action == "BUY" else 81
        decision.risk_reward = risk.risk_reward = 19 / 7
        risk.valid = risk.approved = sample.get("risk", True)
        return context


def engine(samples):
    return ReplayEngine(OfflinePipeline(samples), trusted_offline=True)


class ReplayCurrentDecisionTests(unittest.TestCase):
    def test_strategy_with_wait_is_not_authority(self):
        result = engine([{"action": "WAIT"}]).executar(AnalysisContext(), [bar(0)])
        self.assertEqual(result.operations, 0)

    def test_risk_rejection_prevents_trade(self):
        result = engine([{"action": "BUY", "risk": False}]).executar(AnalysisContext(), [bar(0)])
        self.assertEqual(result.operations, 0)

    def test_invalid_decision_prevents_trade(self):
        result = engine([{"action": "BUY", "valid": False}]).executar(AnalysisContext(), [bar(0)])
        self.assertEqual(result.operations, 0)

    def test_buy_and_sell_decisions_open_and_close(self):
        for direction in ("BUY", "SELL"):
            replay = engine([{"action": direction}])
            result = replay.executar(AnalysisContext(), [bar(0)])
            self.assertEqual(result.operations, 1)
            self.assertFalse(replay.simulator.opened)

    def test_opening_does_not_register_realized_operation(self):
        replay = engine([{"action": "BUY"}, {"action": "WAIT"}])
        def stream():
            yield bar(0, high=125, low=85)
            self.assertTrue(replay.simulator.opened)
            self.assertEqual(replay.statistics.result.operations, 0)
            yield bar(1, high=120)
            self.assertFalse(replay.simulator.opened)
            self.assertEqual(replay.statistics.result.operations, 1)
        result = replay.executar(AnalysisContext(), stream())
        self.assertEqual((result.operations, result.gross_profit), (1, 19))

    def test_wait_invalid_strategy_and_risk_do_not_stop_monitoring(self):
        samples = [{"action": "BUY", "setup": "ENTRY"},
                   {"action": "WAIT", "strategy_valid": False, "risk": False, "setup": "LATER"}]
        result = engine(samples).executar(AnalysisContext(), [bar(0), bar(1, low=92)])
        self.assertEqual((result.operations, result.gross_loss), (1, 7))
        self.assertEqual(set(result.setups), {"ENTRY"})

    def test_new_signal_does_not_overwrite_original_position(self):
        samples = [{"action": "BUY", "setup": "FIRST"},
                   {"action": "SELL", "setup": "SECOND"},
                   {"action": "WAIT"}]
        replay = engine(samples)
        result = replay.executar(AnalysisContext(), [bar(0), bar(1), bar(2, high=120)])
        self.assertEqual((result.operations, result.gross_profit), (1, 19))
        self.assertEqual(set(result.setups), {"FIRST"})

    def test_session_end_exactly_once(self):
        replay = engine([{"action": "BUY"}, {"action": "WAIT", "close": 104}])
        with patch.object(replay, "_register", wraps=replay._register) as register:
            result = replay.executar(AnalysisContext(), [bar(0), bar(1, high=105, close=104)])
        closed = [call.args[0] for call in register.call_args_list if call.args[0] is not None]
        self.assertEqual(len(closed), 1)
        self.assertEqual((closed[0].reason, result.operations, result.net_profit), ("SESSION_END", 1, 4))

    def test_empty_second_session_resets_and_previous_result_is_independent(self):
        replay = engine([{"action": "BUY"}])
        first = replay.executar(AnalysisContext(), [bar(0)])
        before = copy.deepcopy(first)
        # Even a position inserted between calls must not be inherited.
        replay.simulator.trade = SimpleNamespace(opened=True)
        second = replay.executar(AnalysisContext(), [])
        self.assertEqual((second.candles, second.operations), (0, 0))
        self.assertFalse(replay.simulator.opened)
        self.assertEqual(first, before)
        self.assertEqual(second.order_flow_metrics["observations"], 0)

    def test_repeated_sessions_are_deterministic_and_pipeline_not_reused(self):
        replay = engine([{"action": "BUY"}])
        first = replay.executar(AnalysisContext(), [bar(0)])
        second = replay.executar(AnalysisContext(), [bar(0)])
        self.assertEqual(first, second)
        self.assertEqual(replay.pipeline.index, 0)
        self.assertIsNot(first, second)
        second.setups["ORIGINAL"]["operations"] = 999
        self.assertEqual(first.setups["ORIGINAL"]["operations"], 1)

    def test_prior_context_is_rejected_without_reset(self):
        replay = engine([{"action": "WAIT"}])
        context = AnalysisContext()
        replay.executar(context, [bar(0)])
        before = pickle.dumps(context)
        with self.assertRaises(ValueError):
            replay.executar(context, [])
        self.assertEqual(pickle.dumps(context), before)

    def test_invalid_temporal_candle_does_not_reach_pipeline_or_market(self):
        for second in (bar(0), bar(-1), bar(1, timestamp=None), bar(1, high=98)):
            replay = engine([{"action": "WAIT"}])
            context = AnalysisContext()
            with self.assertRaises(ValueError):
                replay.executar(context, [bar(0), second])
            self.assertEqual(context.market.candle_count, 1)

    def test_live_resources_rejected_without_invocation(self):
        for resource in ReplayEngine._LIVE_RESOURCES:
            pipeline = OfflinePipeline([])
            setattr(pipeline, resource, object())
            with self.assertRaises(ValueError):
                ReplayEngine(pipeline, trusted_offline=True).executar(AnalysisContext(), [])
            self.assertEqual(pipeline.index, 0)

    def test_unisolatable_pipeline_fails_closed(self):
        class SharedPipeline(OfflinePipeline):
            def __deepcopy__(self, memo):
                return self
        with self.assertRaises(ValueError):
            ReplayEngine(SharedPipeline([]), trusted_offline=True).executar(AnalysisContext(), [])

    def test_injected_known_metrics_preserved_and_reset(self):
        metrics = OrderFlowExperimentMetrics(score_threshold=80)
        replay = ReplayEngine(OfflinePipeline([{"action": "WAIT"}]), metrics, trusted_offline=True)
        result = replay.executar(AnalysisContext(), [bar(0)])
        self.assertIs(replay.order_flow_metrics, metrics)
        self.assertEqual(result.order_flow_metrics["score_threshold"], 80)
        self.assertEqual(result.order_flow_metrics["observations"], 1)
        self.assertEqual(replay.executar(AnalysisContext(), []).order_flow_metrics["observations"], 0)

    def test_unknown_metrics_fail_closed(self):
        with self.assertRaises(TypeError):
            ReplayEngine(OfflinePipeline([]), object(), trusted_offline=True).executar(AnalysisContext(), [])

    def test_pipeline_results_are_not_modified_by_consumer(self):
        context = AnalysisContext()
        replay = engine([{"action": "BUY"}])
        # New simulator is session-owned; observe class entry instead.
        from replay.trade_simulator import TradeSimulator
        simulate = TradeSimulator.simulate
        def checked(simulator, current, candle):
            before = pickle.dumps(current)
            trade = simulate(simulator, current, candle)
            self.assertEqual(pickle.dumps(current), before)
            return trade
        with patch.object(TradeSimulator, "simulate", checked):
            replay.executar(context, [bar(0)])
        self.assertEqual(context.decision.action, "BUY")

    def test_only_offline_dependencies_no_bot_connector_or_gateway(self):
        import ast
        from pathlib import Path
        tree = ast.parse((Path(__file__).resolve().parents[1] / "replay" / "replay_engine.py").read_text(encoding="utf-8-sig"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertEqual(imports, {"copy", "dataclasses", "datetime", "enum", "types", "analysis", "core.analysis_context",
                                  "models.candle", "models.decision_result", "replay.replay_result",
                                  "performance.order_flow_experiment_metrics",
                                  "replay.replay_statistics", "replay.trade_simulator"})


if __name__ == "__main__":
    unittest.main()
