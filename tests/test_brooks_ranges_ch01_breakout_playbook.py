from analysis.price_action.breakout_playbook_dynamics import BreakoutPlaybookDynamics
from models.candle import Candle


def c(o, h, l, close):
    return Candle(open=o, high=h, low=l, close=close)


def test_bull_breakout_with_follow_through():
    candles = [
        c(100, 101, 99, 100.5),
        c(100.5, 102, 100, 101),
        c(101, 102.5, 100.5, 101.5),
        c(101.5, 103, 101, 102),
        c(102, 105, 101.8, 104.8),
        c(104.8, 106, 104, 105.5),
        c(105.5, 106, 104.5, 105),
    ]
    result = BreakoutPlaybookDynamics.analyze(candles)
    assert result["brooks_range_breakout_valid"] is True
    assert result["brooks_range_breakout_direction"] == "BUY"
    assert result["brooks_range_breakout_follow_through"] is True
    assert result["brooks_range_breakout_failed"] is False


def test_bear_breakout_with_follow_through():
    candles = [
        c(100, 101, 99, 100),
        c(100, 100.5, 98.5, 99.5),
        c(99.5, 100, 98, 99),
        c(99, 99.5, 97.5, 98.5),
        c(98.5, 98.7, 95, 95.2),
        c(95.2, 96, 94, 94.5),
        c(94.5, 95, 93.5, 94),
    ]
    result = BreakoutPlaybookDynamics.analyze(candles)
    assert result["brooks_range_breakout_valid"] is True
    assert result["brooks_range_breakout_direction"] == "SELL"
    assert result["brooks_range_breakout_follow_through"] is True


def test_failed_breakout_is_wait():
    candles = [
        c(100, 101, 99, 100.5),
        c(100.5, 102, 100, 101),
        c(101, 102.5, 100.5, 101.5),
        c(101.5, 103, 101, 102),
        c(102, 105, 101.8, 104.8),
        c(104.8, 105, 101, 101.5),
        c(101.5, 102, 100.5, 101),
    ]
    result = BreakoutPlaybookDynamics.analyze(candles)
    assert result["brooks_range_breakout_failed"] is True
    assert result["brooks_range_breakout_state"] == "FAILED_BREAKOUT"
    assert result["brooks_range_breakout_entry_bias"] == "WAIT"


def test_current_bar_cannot_create_breakout():
    candles = [
        c(100, 101, 99, 100.2),
        c(100.2, 101.2, 99.5, 100.4),
        c(100.4, 101.5, 99.8, 100.6),
        c(100.6, 101.6, 100, 100.8),
        c(100.8, 101.7, 100.2, 101),
        c(101, 105, 100.8, 104.8),
    ]
    result = BreakoutPlaybookDynamics.analyze(candles)
    assert result["brooks_range_breakout_valid"] is False
    assert result["brooks_range_breakout_current_bar_excluded"] is True


def test_insufficient_history():
    result = BreakoutPlaybookDynamics.analyze([c(100, 101, 99, 100)])
    assert result["brooks_range_breakout_valid"] is False
