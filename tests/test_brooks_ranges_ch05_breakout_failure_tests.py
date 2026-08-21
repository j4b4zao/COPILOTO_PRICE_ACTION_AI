"""Tests for Brooks Trading Ranges chapter 5 diagnostic layer."""

from dataclasses import dataclass

from analysis.price_action.breakout_failure_test_dynamics import (
    BreakoutFailureTestDynamics,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def _forming():
    return c(0, 999, -999, 0)


def test_buy_breakout_pullback_test_and_resumption():
    candles = [
        c(100, 102, 99, 101),
        c(101, 103, 100, 102),
        c(102, 104, 101, 103),
        c(103, 105, 102, 104),
        c(104, 106, 103, 105),
        c(105, 110, 105, 109),  # breakout above 106
        c(109, 110, 106, 107),  # test holds
        c(107, 112, 107, 111),  # resumption beyond breakout bar
        c(111, 113, 110, 112),
        c(112, 114, 111, 113),
        _forming(),
    ]
    r = BreakoutFailureTestDynamics().analyze(candles)
    assert r.direction == "BUY"
    assert r.breakout_test_detected
    assert r.test_held
    assert r.resumed_beyond_breakout_bar
    assert r.state in {"BREAKOUT_TEST_RESUMPTION", "BREAKOUT_PULLBACK_RESUMPTION"}


def test_sell_breakout_test_and_resumption():
    candles = [
        c(110, 111, 108, 109),
        c(109, 110, 107, 108),
        c(108, 109, 106, 107),
        c(107, 108, 105, 106),
        c(106, 107, 104, 105),
        c(105, 105, 100, 101),  # breakout below 104
        c(101, 104, 100, 103),  # test holds below/at level
        c(103, 103, 98, 99),    # resumption
        c(99, 100, 97, 98),
        c(98, 99, 96, 97),
        _forming(),
    ]
    r = BreakoutFailureTestDynamics().analyze(candles)
    assert r.direction == "SELL"
    assert r.breakout_test_detected
    assert r.test_held
    assert r.resumed_beyond_breakout_bar


def test_failed_buy_breakout_returns_to_range():
    candles = [
        c(100, 102, 99, 101),
        c(101, 103, 100, 102),
        c(102, 104, 101, 103),
        c(103, 105, 102, 104),
        c(104, 106, 103, 105),
        c(105, 110, 105, 109),
        c(109, 109, 103, 104),  # closes back below breakout level 106
        c(104, 105, 101, 102),
        c(102, 104, 100, 101),
        c(101, 103, 99, 100),
        _forming(),
    ]
    r = BreakoutFailureTestDynamics().analyze(candles)
    assert r.failed_breakout
    assert r.state == "FAILED_BREAKOUT"


def test_failed_failure_resumes_original_buy_breakout():
    candles = [
        c(100, 102, 99, 101),
        c(101, 103, 100, 102),
        c(102, 104, 101, 103),
        c(103, 105, 102, 104),
        c(104, 106, 103, 105),
        c(105, 110, 105, 109),
        c(109, 108, 103, 104),  # failure below level
        c(104, 112, 104, 111),  # failure of failure; resumes above breakout bar
        c(111, 113, 110, 112),
        c(112, 114, 111, 113),
        _forming(),
    ]
    r = BreakoutFailureTestDynamics().analyze(candles)
    assert r.failed_breakout
    assert r.failed_failure_resumption
    assert r.state == "FAILED_FAILURE_RESUMPTION"


def test_current_candle_cannot_create_failure_or_resumption():
    candles = [
        c(100, 102, 99, 101),
        c(101, 103, 100, 102),
        c(102, 104, 101, 103),
        c(103, 105, 102, 104),
        c(104, 106, 103, 105),
        c(105, 110, 105, 109),
        c(109, 111, 107, 110),
        c(110, 112, 108, 111),
        c(111, 113, 109, 112),
        c(112, 114, 110, 113),
        c(113, 114, 100, 101),  # forming candle would imply failure, must be ignored
    ]
    r = BreakoutFailureTestDynamics().analyze(candles)
    assert not r.failed_breakout


def test_insufficient_history():
    r = BreakoutFailureTestDynamics().analyze([c(1, 2, 0, 1)] * 6)
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons
