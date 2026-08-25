from dataclasses import dataclass

from analysis.price_action.always_in_dynamics import AlwaysInDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def _with_current(closed, current=None):
    return closed + [current or C(100, 101, 99, 100)]


def test_insufficient_history():
    r = AlwaysInDynamics().analyze(_with_current([C(1, 2, 0, 1.5)] * 5))
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_always_in_long_from_persistent_bull_control():
    closed = [
        C(100, 102, 99.8, 101.8),
        C(101.7, 103, 101.5, 102.8),
        C(102.7, 104, 102.5, 103.8),
        C(103.7, 105, 103.5, 104.7),
        C(104.6, 106, 104.4, 105.8),
        C(105.7, 107, 105.5, 106.8),
        C(106.7, 108.5, 106.5, 108.2),
        C(108.1, 110, 108.0, 109.8),
    ]
    r = AlwaysInDynamics().analyze(_with_current(closed))
    assert r.valid is True
    assert r.status == "ALWAYS_IN_LONG"
    assert r.direction == "BUY"


def test_always_in_short_from_persistent_bear_control():
    closed = [
        C(110, 110.2, 108, 108.2),
        C(108.3, 108.5, 106.5, 106.7),
        C(106.8, 107, 105, 105.2),
        C(105.3, 105.5, 103.5, 103.7),
        C(103.8, 104, 102, 102.2),
        C(102.3, 102.5, 100.5, 100.7),
        C(100.8, 101, 98.8, 99.0),
        C(99.1, 99.3, 97.0, 97.2),
    ]
    r = AlwaysInDynamics().analyze(_with_current(closed))
    assert r.status == "ALWAYS_IN_SHORT"
    assert r.direction == "SELL"


def test_single_opposite_bar_does_not_flip():
    closed = [
        C(100, 102, 99.8, 101.8), C(101.7, 103, 101.5, 102.8),
        C(102.7, 104, 102.5, 103.8), C(103.7, 105, 103.5, 104.7),
        C(104.6, 106, 104.4, 105.8), C(105.7, 107, 105.5, 106.8),
        C(106.8, 107, 104.0, 104.3), C(104.3, 105, 103.8, 104.6),
    ]
    r = AlwaysInDynamics().analyze(_with_current(closed), previous_direction="BUY")
    assert r.flip_confirmed is False
    assert r.direction != "SELL"


def test_opposite_breakout_without_follow_through_is_possible_flip_only():
    closed = [
        C(100, 102, 99.8, 101.8), C(101.7, 103, 101.5, 102.8),
        C(102.7, 104, 102.5, 103.8), C(103.7, 105, 103.5, 104.7),
        C(104.6, 106, 104.4, 105.8), C(105.7, 107, 105.5, 106.8),
        C(106.8, 107, 98.0, 98.5), C(98.5, 100, 98.2, 99.5),
    ]
    r = AlwaysInDynamics().analyze(_with_current(closed), previous_direction="BUY")
    assert r.possible_flip is True
    assert r.flip_confirmed is False
    assert r.status == "POSSIBLE_FLIP"
    assert r.direction == "BUY"


def test_current_candle_is_ignored():
    closed = [C(100 + i, 102 + i, 99.8 + i, 101.8 + i) for i in range(8)]
    a = AlwaysInDynamics().analyze(_with_current(closed, C(108, 109, 50, 51)))
    b = AlwaysInDynamics().analyze(_with_current(closed, C(108, 160, 107, 159)))
    assert a.to_dict() == b.to_dict()
