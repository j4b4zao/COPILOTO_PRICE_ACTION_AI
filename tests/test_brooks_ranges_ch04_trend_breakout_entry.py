from dataclasses import dataclass

from analysis.price_action.trend_breakout_entry_dynamics import (
    TrendBreakoutEntryDynamics,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def test_strong_bull_trend_breakout_after_pullback():
    candles = [
        c(100, 102, 99.8, 101.8),
        c(101.8, 104, 101.5, 103.8),
        c(103.8, 106, 103.5, 105.7),
        c(105.7, 108, 105.4, 107.8),
        c(107.8, 110, 107.5, 109.8),
        c(109.8, 111, 109.5, 110.8),
        c(110.8, 111.0, 109.6, 110.0),
        c(110.0, 110.2, 108.9, 109.2),
        c(109.2, 112.8, 109.0, 112.5),
        c(112.5, 114.0, 112.2, 113.8),
        c(113.8, 115.0, 113.5, 114.8),
        c(114.8, 115.2, 114.2, 114.6),
        c(114.6, 115.3, 114.4, 115.0),
    ]
    result = TrendBreakoutEntryDynamics().analyze(candles)
    assert result.valid is True
    assert result.direction == "BUY"
    assert result.trend_aligned_breakout is True
    assert result.pullback_present is True
    assert result.state in {
        "STRONG_TREND_BREAKOUT_ENTRY",
        "TREND_BREAKOUT_ENTRY_CANDIDATE",
    }


def test_strong_bear_trend_breakout_after_pullback():
    candles = [
        c(120, 120.2, 118, 118.2),
        c(118.2, 118.5, 116, 116.2),
        c(116.2, 116.5, 114, 114.2),
        c(114.2, 114.5, 112, 112.2),
        c(112.2, 112.5, 110, 110.2),
        c(110.2, 110.5, 109, 109.2),
        c(109.2, 110.4, 109.0, 110.0),
        c(110.0, 111.1, 109.8, 110.9),
        c(110.9, 111.0, 107.2, 107.5),
        c(107.5, 107.8, 106.0, 106.2),
        c(106.2, 106.5, 105.0, 105.2),
        c(105.2, 105.8, 104.8, 105.0),
        c(105.0, 105.3, 104.5, 104.8),
    ]
    result = TrendBreakoutEntryDynamics().analyze(candles)
    assert result.valid is True
    assert result.direction == "SELL"
    assert result.pullback_present is True


def test_no_setup_without_strong_prior_trend():
    candles = [
        c(100, 101, 99, 100.3), c(100.3, 101.2, 99.5, 100.0),
        c(100, 101, 99.2, 100.5), c(100.5, 101.1, 99.6, 100.1),
        c(100.1, 101.0, 99.4, 100.4), c(100.4, 101.2, 99.7, 100.0),
        c(100, 101.1, 99.3, 100.2), c(100.2, 101.0, 99.5, 100.1),
        c(100.1, 101.3, 99.6, 100.3), c(100.3, 101.0, 99.8, 100.0),
        c(100.0, 101.2, 99.6, 100.2), c(100.2, 101.0, 99.7, 100.1),
        c(100.1, 101.5, 99.9, 101.2),
    ]
    result = TrendBreakoutEntryDynamics().analyze(candles)
    assert result.valid is False


def test_current_candle_cannot_create_setup():
    closed = [
        c(100, 102, 99.8, 101.8), c(101.8, 104, 101.5, 103.8),
        c(103.8, 106, 103.5, 105.7), c(105.7, 108, 105.4, 107.8),
        c(107.8, 110, 107.5, 109.8), c(109.8, 111, 109.5, 110.8),
        c(110.8, 111.0, 109.6, 110.0), c(110.0, 110.2, 108.9, 109.2),
        c(109.2, 110.0, 108.8, 109.5), c(109.5, 110.1, 109.0, 109.6),
        c(109.6, 110.0, 109.1, 109.5), c(109.5, 110.0, 109.0, 109.4),
    ]
    current_breakout = c(109.4, 113.0, 109.3, 112.8)
    result = TrendBreakoutEntryDynamics().analyze(closed + [current_breakout])
    assert result.valid is False


def test_insufficient_history():
    candles = [c(100, 101, 99, 100.5)] * 6
    result = TrendBreakoutEntryDynamics().analyze(candles)
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
