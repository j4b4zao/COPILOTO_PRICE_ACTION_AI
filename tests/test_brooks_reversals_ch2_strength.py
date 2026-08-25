from dataclasses import dataclass

from analysis.price_action.reversal_strength_dynamics import ReversalStrengthDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_strong_buy_reversal_strength_confirmed():
    closed = [
        C(110, 111, 106, 107),
        C(107, 108, 103, 104),
        C(104, 106, 101, 102),
        C(102, 106, 101, 105),
        C(105, 110, 104, 109),
        C(109, 114, 108, 113),
        C(113, 118, 112, 117),
    ]
    current = C(117, 130, 100, 118)
    r = ReversalStrengthDynamics().analyze(closed + [current], "BUY", structural_break=True)
    assert r.valid is True
    assert r.direction == "BUY"
    assert r.state == "REVERSAL_STRENGTH_CONFIRMED"
    assert r.strong_reversal is True
    assert r.follow_through is True
    assert r.score >= 70


def test_strong_sell_reversal_strength_confirmed():
    closed = [
        C(100, 104, 99, 103),
        C(103, 107, 102, 106),
        C(106, 110, 105, 109),
        C(109, 110, 105, 106),
        C(106, 107, 101, 102),
        C(102, 103, 97, 98),
        C(98, 99, 93, 94),
    ]
    current = C(94, 120, 80, 93)
    r = ReversalStrengthDynamics().analyze(closed + [current], "SELL", structural_break=True)
    assert r.valid is True
    assert r.direction == "SELL"
    assert r.state == "REVERSAL_STRENGTH_CONFIRMED"
    assert r.strong_reversal is True
    assert r.follow_through is True


def test_single_reversal_bar_is_not_enough():
    closed = [
        C(100, 102, 98, 101),
        C(101, 103, 99, 100),
        C(100, 102, 98, 101),
        C(101, 103, 99, 100),
        C(100, 102, 98, 101),
        C(101, 106, 100, 105),
        C(105, 106, 102, 103),
    ]
    current = C(103, 120, 90, 119)
    r = ReversalStrengthDynamics().analyze(closed + [current], "BUY")
    assert r.strong_reversal is False
    assert r.state != "REVERSAL_STRENGTH_CONFIRMED"


def test_current_candle_cannot_create_confirmation():
    closed = [
        C(100, 102, 98, 101),
        C(101, 103, 99, 100),
        C(100, 102, 98, 101),
        C(101, 103, 99, 100),
        C(100, 102, 98, 101),
        C(101, 103, 99, 100),
        C(100, 102, 98, 101),
    ]
    current = C(101, 115, 101, 115)
    r = ReversalStrengthDynamics().analyze(closed + [current], "BUY", structural_break=True)
    assert r.strong_reversal is False
    assert r.directional_bars <= 4


def test_invalid_direction():
    candles = [C(1, 2, 0, 1)] * 8
    r = ReversalStrengthDynamics().analyze(candles, "NONE")
    assert r.valid is False
    assert r.reason == "INVALID_DIRECTION"


def test_insufficient_history():
    candles = [C(1, 2, 0, 1)] * 5
    r = ReversalStrengthDynamics().analyze(candles, "BUY")
    assert r.valid is False
    assert r.reason == "INSUFFICIENT_HISTORY"
