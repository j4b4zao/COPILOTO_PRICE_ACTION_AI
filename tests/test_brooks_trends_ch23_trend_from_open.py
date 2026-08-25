"""Testes da camada diagnostica inspirada em Brooks Trends, capitulo 23."""

from analysis.price_action.trend_from_open_dynamics import TrendFromOpenDynamics
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close):
    return Candle(open=open_, high=high, low=low, close=close, volume=1000.0)


def current_noise():
    return candle(100, 1000, -1000, 100)


def analyze(closed, trend):
    return TrendFromOpenDynamics.analyze([*closed, current_noise()], trend)


def bullish_small_pullback():
    return [
        candle(100.0, 101.4, 99.9, 101.2),
        candle(101.2, 102.7, 101.0, 102.5),
        candle(102.5, 104.0, 102.3, 103.8),
        candle(103.8, 105.1, 103.6, 104.9),
        candle(104.9, 105.4, 104.4, 104.7),
        candle(104.7, 106.2, 104.6, 106.0),
        candle(106.0, 107.6, 105.8, 107.4),
        candle(107.4, 108.8, 107.2, 108.6),
        candle(108.6, 109.0, 108.1, 108.4),
        candle(108.4, 110.0, 108.3, 109.8),
        candle(109.8, 111.4, 109.7, 111.2),
        candle(111.2, 112.7, 111.0, 112.5),
    ]


def bearish_small_pullback():
    return [
        candle(120.0, 120.1, 118.6, 118.8),
        candle(118.8, 119.0, 117.3, 117.5),
        candle(117.5, 117.7, 116.0, 116.2),
        candle(116.2, 116.4, 114.9, 115.1),
        candle(115.1, 115.6, 114.6, 115.3),
        candle(115.3, 115.4, 113.8, 114.0),
        candle(114.0, 114.2, 112.4, 112.6),
        candle(112.6, 112.8, 111.2, 111.4),
        candle(111.4, 111.9, 111.0, 111.6),
        candle(111.6, 111.7, 110.0, 110.2),
        candle(110.2, 110.3, 108.6, 108.8),
        candle(108.8, 109.0, 107.3, 107.5),
    ]


def test_bull_trend_from_open_and_small_pullback():
    metrics = analyze(bullish_small_pullback(), Trend.UP)
    assert metrics["brooks_open_trend_valid"] is True
    assert metrics["brooks_open_trend_direction"] == "BUY"
    assert metrics["brooks_open_trend_from_open"] is True
    assert metrics["brooks_open_trend_small_pullback"] is True
    assert metrics["brooks_open_trend_state"] == "TREND_FROM_OPEN_SMALL_PULLBACK"
    assert metrics["brooks_open_trend_holds_open"] is True
    assert metrics["brooks_open_trend_with_trend_only"] is True


def test_bear_trend_from_open_is_symmetric():
    metrics = analyze(bearish_small_pullback(), Trend.DOWN)
    assert metrics["brooks_open_trend_valid"] is True
    assert metrics["brooks_open_trend_direction"] == "SELL"
    assert metrics["brooks_open_trend_from_open"] is True
    assert metrics["brooks_open_trend_small_pullback"] is True
    assert metrics["brooks_open_trend_holds_open"] is True


def test_sideways_does_not_confirm_regime():
    metrics = analyze(bullish_small_pullback(), Trend.SIDEWAYS)
    assert metrics["brooks_open_trend_valid"] is False
    assert metrics["brooks_open_trend_state"] == "NO_DIRECTIONAL_TREND"
    assert metrics["brooks_open_trend_from_open"] is False


def test_deep_pullback_blocks_small_pullback_label():
    candles = bullish_small_pullback()[:8] + [
        candle(108.6, 108.8, 104.0, 104.5),
        candle(104.5, 106.0, 104.3, 105.8),
        candle(105.8, 107.0, 105.5, 106.8),
    ]
    metrics = analyze(candles, Trend.UP)
    assert metrics["brooks_open_trend_max_pullback_ratio"] > 1.25
    assert metrics["brooks_open_trend_small_pullback"] is False


def test_countertrend_sequence_reduces_strength():
    strong = analyze(bullish_small_pullback(), Trend.UP)
    weak_history = bullish_small_pullback()[:7] + [
        candle(107.4, 107.5, 106.3, 106.5),
        candle(106.5, 106.7, 105.5, 105.7),
        candle(105.7, 106.0, 104.8, 105.0),
        candle(105.0, 106.3, 104.9, 106.1),
    ]
    weak = analyze(weak_history, Trend.UP)
    assert weak["brooks_open_trend_counter_sequence"] >= 3
    assert weak["brooks_open_trend_score"] < strong["brooks_open_trend_score"]


def test_current_candle_is_excluded_from_confirmation():
    closed = bullish_small_pullback()
    destructive_current = candle(112.5, 113.0, 80.0, 81.0)
    metrics = TrendFromOpenDynamics.analyze(
        [*closed, destructive_current],
        Trend.UP,
    )
    baseline = analyze(closed, Trend.UP)
    assert metrics["brooks_open_trend_state"] == baseline["brooks_open_trend_state"]
    assert metrics["brooks_open_trend_score"] == baseline["brooks_open_trend_score"]
    assert metrics["brooks_open_trend_last_close"] == baseline["brooks_open_trend_last_close"]


def test_waiting_for_deep_pullback_is_flagged_in_strong_case():
    metrics = analyze(bullish_small_pullback(), Trend.UP)
    assert metrics["brooks_open_trend_small_pullback"] is True
    assert metrics["brooks_open_trend_score"] >= 70
    assert metrics["brooks_open_trend_wait_deep_pullback_risk"] is True


def test_too_few_closed_bars_returns_empty():
    metrics = analyze(bullish_small_pullback()[:5], Trend.UP)
    assert metrics["brooks_open_trend_valid"] is False
    assert metrics["brooks_open_trend_state"] == "NO_TREND"
