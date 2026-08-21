from dataclasses import dataclass

from analysis.price_action.first_pullback_sequence_dynamics import (
    FirstPullbackSequenceDynamics,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def test_strong_uptrend_first_small_pullback_keeps_continuation_bias():
    candles = [
        c(100, 102, 99.8, 101.8),
        c(101.8, 104, 101.6, 103.8),
        c(103.8, 106, 103.6, 105.8),
        c(105.8, 108, 105.6, 107.8),
        c(107.8, 110, 107.6, 109.8),
        c(109.8, 112, 109.6, 111.8),
        c(111.8, 114, 111.6, 113.8),
        c(113.8, 116, 113.6, 115.8),
        c(115.8, 118, 115.6, 117.8),
        c(117.8, 120, 117.6, 119.8),
        c(119.8, 121, 118.8, 119.1),
        c(119.1, 120.2, 118.5, 119.7),
        c(119.7, 122.0, 119.6, 121.8),
        c(121.8, 122.2, 120.0, 120.4),
        c(120.4, 120.8, 119.8, 120.1),  # current/forming
    ]
    r = FirstPullbackSequenceDynamics().analyze(candles)
    assert r.valid is True
    assert r.direction == "UP"
    assert r.stage_index >= 1
    assert r.continuation_bias is True or r.stage_index > 3


def test_mature_uptrend_can_flag_trading_range_transition():
    candles = [
        c(100, 103, 99.5, 102.8),
        c(102.8, 106, 102.5, 105.7),
        c(105.7, 109, 105.2, 108.7),
        c(108.7, 112, 108.4, 111.5),
        c(111.5, 114, 111.0, 113.6),
        c(113.6, 115, 111.7, 112.2),
        c(112.2, 114.1, 111.2, 113.8),
        c(113.8, 114.5, 110.8, 111.1),
        c(111.1, 113.2, 110.5, 112.8),
        c(112.8, 113.3, 109.7, 110.2),
        c(110.2, 112.7, 109.9, 112.3),
        c(112.3, 113.0, 109.5, 110.1),
        c(110.1, 112.4, 109.8, 112.0),
        c(112.0, 112.7, 109.6, 110.3),
        c(110.3, 112.2, 109.9, 111.8),
        c(111.8, 112.0, 110.8, 111.0),  # current/forming
    ]
    r = FirstPullbackSequenceDynamics().analyze(candles)
    assert r.direction in {"UP", "NONE"} or r.valid is False
    if r.valid:
        assert 0.0 <= r.trend_maturity_score <= 100.0


def test_downtrend_is_supported_symmetrically():
    candles = [
        c(120, 120.2, 118, 118.2),
        c(118.2, 118.4, 116, 116.2),
        c(116.2, 116.4, 114, 114.2),
        c(114.2, 114.4, 112, 112.2),
        c(112.2, 112.4, 110, 110.2),
        c(110.2, 110.4, 108, 108.2),
        c(108.2, 108.4, 106, 106.2),
        c(106.2, 106.4, 104, 104.2),
        c(104.2, 104.4, 102, 102.2),
        c(102.2, 102.4, 100, 100.2),
        c(100.2, 101.5, 99.8, 101.1),
        c(101.1, 101.5, 99.4, 99.7),
        c(99.7, 100.0, 97.5, 97.8),
        c(97.8, 98.8, 97.5, 98.5),
        c(98.5, 98.8, 97.9, 98.1),  # current/forming
    ]
    r = FirstPullbackSequenceDynamics().analyze(candles)
    assert r.valid is True
    assert r.direction == "DOWN"


def test_current_candle_is_excluded_from_confirmation():
    base = [
        c(100, 102, 99.8, 101.8),
        c(101.8, 104, 101.6, 103.8),
        c(103.8, 106, 103.6, 105.8),
        c(105.8, 108, 105.6, 107.8),
        c(107.8, 110, 107.6, 109.8),
        c(109.8, 112, 109.6, 111.8),
        c(111.8, 114, 111.6, 113.8),
        c(113.8, 116, 113.6, 115.8),
        c(115.8, 118, 115.6, 117.8),
        c(117.8, 120, 117.6, 119.8),
        c(119.8, 122, 119.6, 121.8),
        c(121.8, 124, 121.6, 123.8),
        c(123.8, 126, 123.6, 125.8),
        c(125.8, 128, 125.6, 127.8),
    ]
    r1 = FirstPullbackSequenceDynamics().analyze(base + [c(127.8, 128, 110, 111)])
    r2 = FirstPullbackSequenceDynamics().analyze(base + [c(127.8, 140, 127, 139)])
    assert r1.to_dict() == r2.to_dict()


def test_insufficient_history():
    r = FirstPullbackSequenceDynamics().analyze([
        c(100, 101, 99, 100.5),
        c(100.5, 102, 100, 101.5),
    ])
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons
