from dataclasses import dataclass

from analysis.price_action.first_leg_measured_move_dynamics import (
    FirstLegMeasuredMoveDynamics,
)


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def current():
    return C(999, 1001, 998, 1000)


def test_buy_spike_projects_measured_move_target():
    candles = [
        C(100, 102, 99, 101),
        C(101, 108, 101, 107),
        C(107, 114, 106, 113),
        C(113, 120, 112, 119),
        C(119, 120, 116, 117),
        C(117, 123, 116, 122),
        C(122, 128, 121, 127),
        C(127, 130, 126, 129),
        current(),
    ]
    r = FirstLegMeasuredMoveDynamics().analyze(candles)
    assert r.valid is True
    assert r.direction == "BUY"
    assert r.measured_move_target > r.spike_end_price
    assert r.spike_size > 0


def test_sell_spike_projects_lower_target():
    candles = [
        C(130, 131, 128, 129),
        C(129, 129, 121, 122),
        C(122, 123, 114, 115),
        C(115, 116, 108, 109),
        C(109, 112, 108, 111),
        C(111, 112, 105, 106),
        C(106, 107, 101, 102),
        C(102, 104, 100, 101),
        current(),
    ]
    r = FirstLegMeasuredMoveDynamics().analyze(candles)
    assert r.valid is True
    assert r.direction == "SELL"
    assert r.measured_move_target < r.spike_end_price


def test_target_reached_creates_profit_taking_zone():
    candles = [
        C(100, 101, 99, 100),
        C(100, 108, 100, 107),
        C(107, 115, 106, 114),
        C(114, 115, 112, 113),
        C(113, 122, 112, 121),
        C(121, 129, 120, 128),
        C(128, 131, 127, 130),
        C(130, 132, 129, 131),
        current(),
    ]
    r = FirstLegMeasuredMoveDynamics().analyze(candles)
    assert r.valid is True
    assert r.target_reached is True
    assert r.profit_taking_zone is True
    assert r.state in {"TARGET_REACHED", "TARGET_OVERSHOT"}


def test_current_candle_cannot_create_target_hit():
    candles = [
        C(100, 101, 99, 100),
        C(100, 108, 100, 107),
        C(107, 115, 106, 114),
        C(114, 115, 112, 113),
        C(113, 117, 112, 116),
        C(116, 119, 115, 118),
        C(118, 120, 117, 119),
        C(119, 121, 118, 120),
        C(120, 200, 119, 199),  # forming/current only
    ]
    r = FirstLegMeasuredMoveDynamics().analyze(candles)
    assert r.valid is True
    assert r.target_reached is False


def test_insufficient_history():
    r = FirstLegMeasuredMoveDynamics().analyze([C(1, 2, 0, 1)] * 5)
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons
