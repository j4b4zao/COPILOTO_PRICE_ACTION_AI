from dataclasses import dataclass

from analysis.price_action.breakout_strength_dynamics import BreakoutStrengthDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_strong_buy_breakout():
    candles = [
        C(100, 101, 99, 100.5), C(100.5, 102, 100, 101),
        C(101, 103, 100.5, 102), C(102, 103, 101, 102.5),
        C(102.5, 104, 102, 103), C(103, 104, 102, 103.5),
        C(103.5, 108, 103.4, 107.8),
        C(107.8, 110, 107.5, 109.5), C(109.5, 112, 109, 111.5),
        C(111.5, 113, 111, 112.5),
        C(112.5, 120, 90, 95),  # forming/current; must be ignored
    ]
    r = BreakoutStrengthDynamics().analyze(candles)
    assert r.valid is True
    assert r.direction == "BUY"
    assert r.strong_breakout is True
    assert r.strong_follow_through is True
    assert r.failed_breakout_risk is False


def test_strong_sell_breakout():
    candles = [
        C(110, 111, 109, 110), C(110, 111, 108, 109),
        C(109, 110, 107, 108), C(108, 109, 107, 108),
        C(108, 109, 106, 107), C(107, 108, 106, 107),
        C(107, 107.2, 102, 102.2),
        C(102.2, 102.5, 99, 99.5), C(99.5, 100, 97, 97.5),
        C(97.5, 98, 96, 96.5),
        C(96.5, 120, 95, 118),
    ]
    r = BreakoutStrengthDynamics().analyze(candles)
    assert r.valid is True
    assert r.direction == "SELL"
    assert r.strong_breakout is True


def test_immediate_rejection_flags_failure_risk():
    candles = [
        C(100, 101, 99, 100), C(100, 102, 99, 101),
        C(101, 103, 100, 102), C(102, 103, 101, 102),
        C(102, 104, 101, 103), C(103, 104, 102, 103),
        C(103, 108, 103, 107.5),
        C(107.5, 108, 102, 103), C(103, 104, 101, 102),
        C(102, 103, 101, 102),
        C(102, 103, 101, 102),
    ]
    r = BreakoutStrengthDynamics().analyze(candles)
    assert r.valid is True
    assert r.immediate_rejection is True
    assert r.failed_breakout_risk is True


def test_current_candle_cannot_create_breakout():
    candles = [
        C(100, 101, 99, 100), C(100, 102, 99, 101),
        C(101, 103, 100, 102), C(102, 103, 101, 102),
        C(102, 104, 101, 103), C(103, 104, 102, 103),
        C(103, 104, 102, 103), C(103, 104, 102, 103),
        C(103, 104, 102, 103),
        C(103, 120, 103, 119),
    ]
    r = BreakoutStrengthDynamics().analyze(candles)
    assert r.valid is False


def test_insufficient_history():
    r = BreakoutStrengthDynamics().analyze([C(1, 2, 0, 1)] * 5)
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons
