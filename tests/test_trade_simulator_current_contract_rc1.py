"""Offline contract and execution tests; runnable with unittest or pytest."""
import ast
import copy
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from core.analysis_context import AnalysisContext
from models.candle import Candle
from replay.trade_simulator import TradeSimulator


T0 = datetime(2026, 10, 7, 10)


def candle(minute=0, *, opening=100, high=101, low=99, close=100):
    return Candle(open=opening, high=high, low=low, close=close,
                  volume=100, timestamp=T0 + timedelta(minutes=minute))


def authorized(direction="BUY", setup="ORIGINAL"):
    context = AnalysisContext()
    decision, risk = context.decision, context.risk
    decision.valid = True
    decision.action = decision.direction = decision.signal = direction
    decision.setup = setup
    decision.entry = risk.entry_price = 100
    decision.stop = risk.stop_loss = 93 if direction == "BUY" else 107
    decision.target = risk.take_profit = 119 if direction == "BUY" else 81
    decision.risk_reward = risk.risk_reward = 19 / 7
    risk.valid = risk.approved = True
    return context


class TradeSimulatorContractTests(unittest.TestCase):
    def test_wait_and_strategy_cannot_authorize(self):
        for strategy_valid in (False, True):
            with self.subTest(strategy_valid=strategy_valid):
                context = authorized()
                context.strategy.valid = strategy_valid
                context.decision.action = "WAIT"
                simulator = TradeSimulator()
                self.assertIsNone(simulator.simulate(context, candle()))
                self.assertFalse(simulator.opened)

    def test_legacy_strategy_is_rejected(self):
        context = authorized()
        context.strategy.valid = True
        context.strategy.signal = "BUY"
        simulator = TradeSimulator()
        self.assertIsNone(simulator.simulate(context.strategy, candle()))
        self.assertEqual(simulator.last_rejection, "UNSUPPORTED_CONTRACT")

    def test_decision_valid_requires_exact_true(self):
        for flag in (False, None, 1):
            context = authorized()
            context.decision.valid = flag
            self.assertIsNone(TradeSimulator().simulate(context, candle()))

    def test_direction_and_signal_must_match(self):
        for name in ("direction", "signal"):
            context = authorized()
            setattr(context.decision, name, "SELL")
            self.assertIsNone(TradeSimulator().simulate(context, candle()))

    def test_risk_requires_both_exact_true_flags(self):
        for name in ("valid", "approved"):
            for flag in (False, None, 1):
                context = authorized()
                setattr(context.risk, name, flag)
                self.assertIsNone(TradeSimulator().simulate(context, candle()))

    def test_buy_official_levels_and_status_not_required(self):
        context = authorized()
        trade = TradeSimulator().simulate(context, candle())
        self.assertEqual((trade.direction, trade.entry, trade.stop, trade.target),
                         ("BUY", 100, 93, 119))
        self.assertEqual(trade.risk_reward, context.decision.risk_reward)
        self.assertEqual(trade.opened_at, T0)
        self.assertEqual(trade.profit, 0)

    def test_sell_official_levels(self):
        trade = TradeSimulator().simulate(authorized("SELL"), candle())
        self.assertEqual((trade.direction, trade.entry, trade.stop, trade.target),
                         ("SELL", 100, 107, 81))

    def test_mismatch_each_field_rejects_without_mutation(self):
        for name in ("entry_price", "stop_loss", "take_profit", "risk_reward"):
            context = authorized()
            setattr(context.risk, name, getattr(context.risk, name) + 1)
            before = pickle.dumps(context)
            simulator = TradeSimulator()
            self.assertIsNone(simulator.simulate(context, candle()))
            self.assertEqual(simulator.last_rejection, "DECISION_RISK_MISMATCH")
            self.assertEqual(pickle.dumps(context), before)

    def test_invalid_numbers_on_both_contracts(self):
        for owner, fields in (("decision", ("entry", "stop", "target", "risk_reward")),
                              ("risk", ("entry_price", "stop_loss", "take_profit", "risk_reward"))):
            for name in fields:
                for value in (float("nan"), float("inf"), 0, -1, True, "100", None):
                    with self.subTest(owner=owner, field=name, value=value):
                        context = authorized()
                        setattr(getattr(context, owner), name, value)
                        self.assertIsNone(TradeSimulator().simulate(context, candle()))

    def test_invalid_geometry(self):
        for direction in ("BUY", "SELL"):
            context = authorized(direction)
            context.decision.stop = context.risk.stop_loss = 100
            simulator = TradeSimulator()
            self.assertIsNone(simulator.simulate(context, candle()))
            self.assertEqual(simulator.last_rejection, "INVALID_GEOMETRY")

    def test_structural_entry_is_not_filled(self):
        simulator = TradeSimulator()
        self.assertIsNone(simulator.simulate(authorized(), candle(close=100.01)))
        self.assertEqual(simulator.last_rejection, "UNSUPPORTED_ENTRY_MODEL")

    def test_narrow_numeric_comparison(self):
        simulator = TradeSimulator()
        self.assertIsNotNone(simulator.simulate(authorized(), candle(close=100 + 1e-10)))
        self.assertEqual(simulator.trade.entry, 100)

    def test_timestamp_required(self):
        for timestamp in (None, "2026-10-07", 123):
            bar = candle()
            bar.timestamp = timestamp
            self.assertIsNone(TradeSimulator().simulate(authorized(), bar))

    def test_invalid_ohlc_rejected(self):
        for bar in (candle(high=98), candle(low=102), candle(close=float("nan"))):
            self.assertIsNone(TradeSimulator().simulate(authorized(), bar))

    def test_existing_position_not_overwritten(self):
        simulator = TradeSimulator()
        trade = simulator.simulate(authorized(), candle())
        before = copy.deepcopy(trade)
        self.assertIsNone(simulator.simulate(authorized("SELL"), candle(1)))
        self.assertIs(simulator.trade, trade)
        self.assertEqual(trade, before)

    def test_opening_bar_cannot_retroactively_close(self):
        simulator = TradeSimulator()
        bar = candle(high=125, low=85)
        trade = simulator.simulate(authorized(), bar)
        before = copy.deepcopy(trade)
        self.assertIsNone(simulator.update(bar))
        self.assertEqual(trade, before)

    def test_duplicate_and_out_of_order_do_not_mutate(self):
        simulator = TradeSimulator()
        simulator.simulate(authorized(), candle())
        simulator.update(candle(2))
        before = copy.deepcopy(simulator.trade)
        for minute in (2, 1, 0, -1):
            self.assertIsNone(simulator.update(candle(minute, high=125, low=85)))
            self.assertEqual(simulator.trade, before)

    def test_incomparable_timestamp_does_not_mutate(self):
        simulator = TradeSimulator()
        simulator.simulate(authorized(), candle())
        bar = candle(1)
        bar.timestamp = bar.timestamp.replace(tzinfo=timezone.utc)
        before = copy.deepcopy(simulator.trade)
        self.assertIsNone(simulator.update(bar))
        self.assertEqual(simulator.trade, before)

    def assert_exit(self, direction, bar, reason, price, profit):
        simulator = TradeSimulator()
        simulator.simulate(authorized(direction), candle())
        trade = simulator.update(bar)
        self.assertIsNotNone(trade)
        self.assertTrue(trade.closed)
        self.assertEqual((trade.reason, trade.exit, trade.profit), (reason, price, profit))
        self.assertFalse(simulator.opened)
        self.assertIsNone(simulator.update(bar))

    def test_buy_stop(self):
        self.assert_exit("BUY", candle(1, low=92), "STOP", 93, -7)

    def test_buy_target(self):
        self.assert_exit("BUY", candle(1, high=120), "TARGET", 119, 19)

    def test_sell_stop(self):
        self.assert_exit("SELL", candle(1, high=108), "STOP", 107, -7)

    def test_sell_target(self):
        self.assert_exit("SELL", candle(1, low=80), "TARGET", 81, 19)

    def test_buy_both_stop_first(self):
        self.assert_exit("BUY", candle(1, high=120, low=92), "STOP", 93, -7)

    def test_sell_both_stop_first(self):
        self.assert_exit("SELL", candle(1, high=108, low=80), "STOP", 107, -7)

    def test_gap_stop_buy(self):
        self.assert_exit("BUY", candle(1, opening=90, high=125, low=89), "GAP_STOP", 90, -10)

    def test_gap_stop_sell(self):
        self.assert_exit("SELL", candle(1, opening=110, high=111, low=79), "GAP_STOP", 110, -10)

    def test_gap_target_buy(self):
        self.assert_exit("BUY", candle(1, opening=125, high=126, low=90), "GAP_TARGET", 119, 19)

    def test_gap_target_sell(self):
        self.assert_exit("SELL", candle(1, opening=75, high=110, low=74), "GAP_TARGET", 81, 19)

    def test_manual_and_session_end_pnl(self):
        for direction, expected in (("BUY", 4), ("SELL", -4)):
            for reason in ("MANUAL", "SESSION_END"):
                simulator = TradeSimulator()
                simulator.simulate(authorized(direction), candle())
                trade = simulator.close(104, reason=reason)
                self.assertEqual((trade.reason, trade.profit), (reason, expected))
                self.assertIsNone(simulator.close(104, reason=reason))

    def test_rejected_close_preserves_position(self):
        simulator = TradeSimulator()
        simulator.simulate(authorized(), candle())
        before = copy.deepcopy(simulator.trade)
        self.assertIsNone(simulator.close(float("nan")))
        self.assertEqual(simulator.trade, before)

    def test_snapshot_and_no_feedback_to_any_core_result(self):
        context = authorized()
        before = pickle.dumps(context)
        simulator = TradeSimulator()
        trade = simulator.simulate(context, candle())
        simulator.update(candle(1))
        simulator.close(104)
        self.assertEqual(pickle.dumps(context), before)
        context.decision.clear()
        context.risk.clear()
        self.assertEqual((trade.entry, trade.stop, trade.target, trade.setup), (100, 93, 119, "ORIGINAL"))

    def test_no_engines_or_order_paths_in_simulator(self):
        source = Path(__file__).resolve().parents[1] / "replay" / "trade_simulator.py"
        tree = ast.parse(source.read_text(encoding="utf-8-sig"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertEqual(set(imports), {"dataclasses", "datetime", "math", "numbers", "core.analysis_context"})
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                             and node.func.attr == "executar" for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
