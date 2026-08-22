from dataclasses import dataclass

from analysis.price_action.previous_day_pattern_dynamics import PreviousDayPatternDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def prev_day():
    return [
        C(100, 103, 99, 102),
        C(102, 105, 101, 104),
        C(104, 106, 102, 105),
    ]


def test_breakout_above_previous_high_needs_follow_through():
    current = [
        C(105, 107, 104, 106.5),
        C(106.5, 108, 106, 107.2),
        C(107.2, 108, 106.8, 107.4),
        C(107.4, 109, 107, 108),  # forming, ignored
    ]
    r = PreviousDayPatternDynamics().analyze(prev_day(), current)
    assert r.status == "PREVIOUS_DAY_BREAKOUT_CONFIRMED"
    assert r.direction == "BUY"
    assert r.follow_through is True


def test_breakout_pullback_retest():
    current = [
        C(105, 107.5, 104.5, 106.8),
        C(106.8, 107.2, 105.8, 106.2),
        C(106.2, 108, 106.0, 107.6),
        C(107.6, 108, 107, 107.8),
    ]
    r = PreviousDayPatternDynamics().analyze(prev_day(), current)
    assert r.status == "PREVIOUS_DAY_BREAKOUT_PULLBACK"
    assert r.breakout_pullback is True


def test_failed_breakout_above_previous_high():
    current = [
        C(105, 107.5, 104.5, 106.8),
        C(106.8, 107, 104.5, 105.0),
        C(105.0, 105.5, 103.5, 104.0),
        C(104, 110, 103, 109),
    ]
    r = PreviousDayPatternDynamics().analyze(prev_day(), current)
    assert r.status == "PREVIOUS_DAY_FAILED_BREAKOUT"
    assert r.direction == "BUY"
    assert r.failed_breakout is True
    assert r.reversal_watch is True


def test_previous_low_breakout_confirmed():
    current = [
        C(100, 100.5, 98, 98.5),
        C(98.5, 99, 97, 97.5),
        C(97.5, 98, 96.5, 97.0),
        C(97, 105, 96, 104),
    ]
    r = PreviousDayPatternDynamics().analyze(prev_day(), current)
    assert r.status == "PREVIOUS_DAY_BREAKOUT_CONFIRMED"
    assert r.direction == "SELL"


def test_forming_candle_cannot_create_breakout():
    current = [
        C(103, 105, 102, 104),
        C(104, 105.5, 103, 105),
        C(105, 105.8, 104, 105.2),
        C(105.2, 109, 105, 108.5),
    ]
    r = PreviousDayPatternDynamics().analyze(prev_day(), current)
    assert r.breakout_confirmed is False


def test_insufficient_history():
    r = PreviousDayPatternDynamics().analyze(prev_day(), [C(100, 101, 99, 100)])
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons
