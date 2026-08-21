"""Testes do capítulo 19 de Trading Price Action Trends."""

from analysis.price_action.trend_strength_dynamics import TrendStrengthDynamics
from enums.trend import Trend
from models.candle import Candle


def candle(open_, high, low, close, volume=1000.0):
    return Candle(
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def current_placeholder():
    return candle(0, 1000, -1000, 0)


def analyze(closed, trend, result=None):
    return TrendStrengthDynamics.analyze(
        [*closed, current_placeholder()],
        trend,
        result=result,
    )


def strong_uptrend():
    return [
        candle(100, 104.2, 99.8, 104.0),
        candle(104.1, 108.2, 104.0, 108.0),
        candle(108.1, 112.3, 108.0, 112.0),
        candle(112.1, 116.4, 112.0, 116.1),
        candle(116.2, 120.5, 116.1, 120.2),
        candle(120.3, 124.6, 120.2, 124.3),
        candle(124.4, 128.8, 124.3, 128.5),
        candle(128.6, 133.0, 128.5, 132.7),
    ]


def strong_downtrend():
    return [
        candle(133.0, 133.2, 128.6, 128.8),
        candle(128.7, 128.8, 124.3, 124.5),
        candle(124.4, 124.5, 120.1, 120.3),
        candle(120.2, 120.3, 116.0, 116.2),
        candle(116.1, 116.2, 112.0, 112.2),
        candle(112.1, 112.2, 108.0, 108.2),
        candle(108.1, 108.2, 104.0, 104.2),
        candle(104.1, 104.2, 100.0, 100.2),
    ]


def overlapping_market():
    return [
        candle(100.0, 101.2, 99.4, 100.5),
        candle(100.6, 101.3, 99.6, 100.1),
        candle(100.0, 101.1, 99.5, 100.6),
        candle(100.5, 101.4, 99.7, 100.0),
        candle(100.1, 101.2, 99.5, 100.7),
        candle(100.8, 101.4, 99.7, 100.2),
        candle(100.1, 101.3, 99.5, 100.6),
        candle(100.7, 101.4, 99.6, 100.1),
    ]


def test_strong_bull_trend_is_classified_as_strong_or_better():
    metrics = analyze(strong_uptrend(), Trend.UP)

    assert metrics["brooks_trend_strength_valid"] is True
    assert metrics["brooks_trend_strength_direction"] == "BUY"
    assert metrics["brooks_trend_strength_state"] in ("STRONG", "VERY_STRONG")
    assert metrics["brooks_trend_strength_score"] >= 70.0
    assert metrics["brooks_trend_strength_aligned_ratio"] == 1.0
    assert metrics["brooks_trend_strength_counter_streak"] == 0
    assert metrics["brooks_trend_strength_urgency"] is True
    assert metrics["brooks_trend_strength_with_trend_only"] is True


def test_strong_bear_trend_is_symmetric():
    metrics = analyze(strong_downtrend(), Trend.DOWN)

    assert metrics["brooks_trend_strength_valid"] is True
    assert metrics["brooks_trend_strength_direction"] == "SELL"
    assert metrics["brooks_trend_strength_state"] in ("STRONG", "VERY_STRONG")
    assert metrics["brooks_trend_strength_score"] >= 70.0
    assert metrics["brooks_trend_strength_aligned_ratio"] == 1.0
    assert metrics["brooks_trend_strength_with_trend_only"] is True


def test_sideways_does_not_create_trend_strength():
    metrics = analyze(strong_uptrend(), Trend.SIDEWAYS)

    assert metrics["brooks_trend_strength_valid"] is False
    assert metrics["brooks_trend_strength_state"] == "NO_TREND"
    assert metrics["brooks_trend_strength_direction"] == "NONE"
    assert metrics["brooks_trend_strength_with_trend_only"] is False


def test_overlap_and_countertrend_follow_through_reduce_strength():
    metrics = analyze(overlapping_market(), Trend.UP)

    assert metrics["brooks_trend_strength_valid"] is True
    assert metrics["brooks_trend_strength_state"] in ("WEAK", "MODERATE")
    assert metrics["brooks_trend_strength_score"] < 70.0
    assert metrics["brooks_trend_strength_overlap_ratio"] > 0.5
    assert metrics["brooks_trend_strength_counter_follow_through"] is False
    assert metrics["brooks_trend_strength_with_trend_only"] is False


def test_two_countertrend_bars_create_follow_through_penalty():
    bars = [
        *strong_uptrend()[:5],
        candle(120.2, 120.5, 117.5, 118.0),
        candle(118.0, 118.3, 115.6, 116.0),
        candle(116.0, 119.5, 115.8, 119.2),
    ]
    metrics = analyze(bars, Trend.UP)

    assert metrics["brooks_trend_strength_counter_streak"] >= 2
    assert metrics["brooks_trend_strength_counter_follow_through"] is True


def test_unconfirmed_current_candle_is_excluded():
    closed = strong_uptrend()
    normal = TrendStrengthDynamics.analyze(
        [*closed, candle(132.7, 133.1, 132.5, 133.0)],
        Trend.UP,
    )
    anomalous = TrendStrengthDynamics.analyze(
        [*closed, candle(132.7, 140.0, 80.0, 81.0)],
        Trend.UP,
    )

    assert normal == anomalous


def test_climax_risk_reduces_score_without_invalidating_context():
    class Result:
        climax_active = True

    baseline = analyze(strong_uptrend(), Trend.UP)
    with_climax = analyze(strong_uptrend(), Trend.UP, Result())

    assert with_climax["brooks_trend_strength_valid"] is True
    assert with_climax["brooks_trend_strength_climax_risk"] is True
    assert with_climax["brooks_trend_strength_score"] < baseline[
        "brooks_trend_strength_score"
    ]
