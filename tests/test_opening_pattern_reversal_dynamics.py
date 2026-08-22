from dataclasses import dataclass

from analysis.price_action.opening_pattern_reversal_dynamics import OpeningPatternReversalDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def current():
    return C(100, 999, 1, 500)


def test_insufficient_history():
    r = OpeningPatternReversalDynamics().analyze([C(100, 101, 99, 100), current()])
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_opening_drive_detected():
    candles = [
        C(100, 103, 99, 102),
        C(102, 105, 101, 104),
        C(104, 107, 103, 106),
        C(106, 107, 104, 105),
        C(105, 106, 103, 104),
        current(),
    ]
    r = OpeningPatternReversalDynamics().analyze(candles)
    assert r.opening_drive is True
    assert r.status == "OPENING_DRIVE"
    assert r.direction == "BUY"


def test_opening_breakout_confirmed_buy():
    candles = [
        C(100, 103, 99, 102),
        C(102, 105, 101, 104),
        C(104, 106, 103, 105),
        C(105, 108, 105, 107),
        C(107, 110, 106, 109),
        C(109, 111, 108, 110),
        current(),
    ]
    r = OpeningPatternReversalDynamics().analyze(candles)
    assert r.status == "OPENING_BREAKOUT_CONFIRMED"
    assert r.direction == "BUY"
    assert r.breakout_follow_through is True


def test_failed_breakout_reversal_sell():
    candles = [
        C(100, 103, 99, 102),
        C(102, 105, 101, 104),
        C(104, 106, 103, 105),
        C(105, 108, 104, 107),
        C(107, 108, 101, 103),
        C(103, 104, 99, 101),
        C(101, 102, 98, 100),
        current(),
    ]
    r = OpeningPatternReversalDynamics().analyze(candles)
    assert r.failed_breakout is True
    assert r.reversal_confirmed is True
    assert r.status == "OPENING_REVERSAL_CONFIRMED"
    assert r.direction == "SELL"


def test_current_forming_candle_cannot_create_breakout():
    base = [
        C(100, 103, 99, 102),
        C(102, 105, 101, 104),
        C(104, 106, 103, 105),
        C(105, 106, 103, 104),
        C(104, 105, 102, 103),
    ]
    r1 = OpeningPatternReversalDynamics().analyze(base + [C(103, 120, 102, 118)])
    r2 = OpeningPatternReversalDynamics().analyze(base + [C(103, 104, 90, 91)])
    assert r1.status == r2.status
    assert r1.breakout_attempt == r2.breakout_attempt


def test_two_sided_open_is_not_directional_confirmation():
    candles = [
        C(100, 103, 99, 102),
        C(102, 105, 101, 104),
        C(104, 106, 103, 105),
        C(105, 108, 104, 107),
        C(107, 108, 97, 98),
        current(),
    ]
    r = OpeningPatternReversalDynamics().analyze(candles)
    assert r.two_sided_open is True
