"""Tests for Brooks Reversals chapter 1 diagnostic layer."""

from dataclasses import dataclass

from analysis.price_action.reversal_trade_example_dynamics import (
    ReversalTradeExampleDynamics,
)


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_insufficient_history():
    candles = [C(10, 11, 9, 10.5) for _ in range(5)]
    result = ReversalTradeExampleDynamics().analyze(candles, old_trend="UP")
    assert result.valid is False
    assert result.reason == "INSUFFICIENT_HISTORY"


def test_unclear_old_trend_rejected():
    candles = [C(10, 11, 9, 10) for _ in range(12)]
    result = ReversalTradeExampleDynamics().analyze(candles, old_trend="SIDEWAYS")
    assert result.valid is False
    assert result.reason == "OLD_TREND_UNCLEAR"


def test_reversal_watch_from_old_trend_exhaustion():
    candles = [
        C(10, 11, 9.8, 10.8),
        C(10.8, 12, 10.6, 11.8),
        C(11.8, 13, 11.6, 12.8),
        C(12.8, 14, 12.6, 13.8),
        C(13.8, 15, 13.5, 14.8),
        C(14.8, 15.2, 14.1, 14.3),
        C(14.3, 15.0, 14.0, 14.8),
        C(14.8, 15.1, 14.0, 14.2),
        C(14.2, 14.8, 13.9, 14.5),
        C(14.5, 15.0, 14.0, 14.1),
        C(14.1, 14.5, 13.8, 14.0),
        C(99, 100, 1, 99),  # current candle: excluded
    ]
    result = ReversalTradeExampleDynamics().analyze(candles, old_trend="UP")
    assert result.valid is True
    assert result.trend_exhaustion is True
    assert result.state in {"REVERSAL_WATCH", "STRUCTURAL_BREAK", "EXTREME_TEST", "REVERSAL_CONFIRMED"}


def test_current_candle_cannot_create_structural_break():
    candles = [
        C(10, 11, 9.8, 10.8),
        C(10.8, 12, 10.6, 11.8),
        C(11.8, 13, 11.6, 12.8),
        C(12.8, 14, 12.6, 13.8),
        C(13.8, 15, 13.5, 14.8),
        C(14.8, 15.2, 14.0, 14.6),
        C(14.6, 15.0, 14.2, 14.7),
        C(14.7, 15.1, 14.3, 14.8),
        C(14.8, 15.2, 14.4, 14.9),
        C(14.9, 15.3, 14.5, 15.0),
        C(15.0, 15.4, 14.6, 15.1),
        C(15.1, 15.2, 5.0, 5.5),  # current candle only breaks structure
    ]
    result = ReversalTradeExampleDynamics().analyze(candles, old_trend="UP")
    assert result.structural_break is False
    assert result.reversal_confirmed is False


def test_result_direction_is_opposite_old_trend():
    candles = [C(20 - i * 0.5, 20.2 - i * 0.5, 19.4 - i * 0.5, 19.6 - i * 0.5) for i in range(12)]
    result = ReversalTradeExampleDynamics().analyze(candles, old_trend="DOWN")
    assert result.valid is True
    assert result.reversal_direction == "BUY"


def test_range_only_risk_when_break_and_test_lack_pressure(monkeypatch):
    engine = ReversalTradeExampleDynamics()
    candles = [C(10, 11, 9, 10.5) for _ in range(12)]

    monkeypatch.setattr(engine, "_trend_exhaustion", lambda *args: True)
    monkeypatch.setattr(engine, "_pivots", lambda *args: ([(2, 12.0)], [(4, 9.0)]))
    monkeypatch.setattr(engine, "_structural_break", lambda *args: (True, 9.0, 6))
    monkeypatch.setattr(engine, "_extreme_test", lambda *args: (True, 12.0, 8, True))
    monkeypatch.setattr(engine, "_opposite_pressure", lambda *args: False)

    result = engine.analyze(candles, old_trend="UP")
    assert result.state == "EXTREME_TEST"
    assert result.range_only_risk is True
    assert result.reversal_confirmed is False


def test_full_sequence_confirms_reversal(monkeypatch):
    engine = ReversalTradeExampleDynamics()
    candles = [C(10, 11, 9, 10.5) for _ in range(12)]

    monkeypatch.setattr(engine, "_trend_exhaustion", lambda *args: True)
    monkeypatch.setattr(engine, "_pivots", lambda *args: ([(2, 12.0)], [(4, 9.0)]))
    monkeypatch.setattr(engine, "_structural_break", lambda *args: (True, 9.0, 6))
    monkeypatch.setattr(engine, "_extreme_test", lambda *args: (True, 12.0, 8, True))
    monkeypatch.setattr(engine, "_opposite_pressure", lambda *args: True)

    result = engine.analyze(candles, old_trend="UP")
    assert result.state == "REVERSAL_CONFIRMED"
    assert result.reversal_confirmed is True
    assert result.reversal_direction == "SELL"
    assert result.quality_score >= 80.0
