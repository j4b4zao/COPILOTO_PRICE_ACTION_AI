from dataclasses import dataclass

from analysis.price_action.double_top_bottom_pullback_dynamics import (
    DoubleTopBottomPullbackDynamics,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def test_invalid_old_trend():
    result = DoubleTopBottomPullbackDynamics().analyze([], "SIDEWAYS")
    assert result.valid is False
    assert "INVALID_OLD_TREND" in result.reasons


def test_insufficient_history():
    candles = [c(10, 11, 9, 10.5)] * 5
    result = DoubleTopBottomPullbackDynamics().analyze(candles, "UP")
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_double_top_pullback_sell_confirmation():
    candles = [
        c(100, 102, 99, 101), c(101, 104, 100, 103), c(103, 106, 102, 105),
        c(105, 108, 104, 107), c(107, 110, 106, 109), c(109, 111, 108, 110),
        c(110, 112, 109, 111), c(111, 113, 110, 112), c(112, 115, 111, 114),
        c(114, 116, 112, 113), c(113, 115.1, 111, 112), c(112, 114, 109, 110),
        c(110, 111, 107, 108),
        c(108, 109, 106, 108),  # current / excluded
    ]
    result = DoubleTopBottomPullbackDynamics().analyze(candles, "UP")
    assert result.pattern == "DOUBLE_TOP_PULLBACK"
    assert result.direction == "SELL"
    assert result.old_trend_continuation_risk in (True, False)
    assert 0.0 <= result.quality_score <= 100.0


def test_double_bottom_pullback_buy_schema():
    candles = [
        c(120, 121, 118, 119), c(119, 120, 116, 117), c(117, 118, 114, 115),
        c(115, 116, 112, 113), c(113, 114, 110, 111), c(111, 112, 109, 110),
        c(110, 111, 108, 109), c(109, 110, 107, 108), c(108, 109, 105, 106),
        c(106, 108, 104, 107), c(107, 109, 105, 108), c(108, 111, 107, 110),
        c(110, 113, 109, 112), c(112, 113, 111, 112),
    ]
    result = DoubleTopBottomPullbackDynamics().analyze(candles, "DOWN")
    assert result.pattern == "DOUBLE_BOTTOM_PULLBACK"
    assert result.direction == "BUY"
    assert isinstance(result.reversal_confirmed, bool)


def test_current_candle_is_excluded():
    base = [c(100 + i, 102 + i, 99 + i, 101 + i) for i in range(11)]
    quiet_current = c(111, 112, 110, 111)
    dramatic_current = c(111, 140, 80, 90)

    a = DoubleTopBottomPullbackDynamics().analyze(base + [quiet_current], "UP")
    b = DoubleTopBottomPullbackDynamics().analyze(base + [dramatic_current], "UP")

    assert a.to_dict() == b.to_dict()
