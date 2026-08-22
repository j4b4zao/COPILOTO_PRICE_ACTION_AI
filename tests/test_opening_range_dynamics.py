from dataclasses import dataclass

from analysis.price_action.opening_range_dynamics import OpeningRangeDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_insufficient_history():
    r = OpeningRangeDynamics().analyze([C(10, 11, 9, 10)] * 4)
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_two_sided_opening_range_enters_breakout_mode():
    bars = [
        C(100, 103, 99, 102), C(102, 103, 99, 100), C(100, 102, 99, 101),
        C(101, 102, 100, 101), C(101, 102, 100, 101), C(101, 102, 100, 101),
    ]
    r = OpeningRangeDynamics().analyze(bars)
    assert r.valid
    assert r.two_sided
    assert r.status == "OPENING_RANGE_BREAKOUT_MODE"


def test_buy_breakout_requires_follow_through():
    bars = [
        C(100, 102, 99, 101), C(101, 103, 100, 102), C(102, 104, 101, 103),
        C(103, 105, 102, 104.5), C(104.5, 106, 104, 105.5), C(105.5, 106, 105, 105.7),
    ]
    r = OpeningRangeDynamics().analyze(bars)
    assert r.status == "OPENING_RANGE_BREAKOUT_CONFIRMED"
    assert r.direction == "BUY"
    assert r.follow_through


def test_breakout_retest_holds_level():
    bars = [
        C(100, 102, 99, 101), C(101, 103, 100, 102), C(102, 104, 101, 103),
        C(103, 105, 103, 104.5), C(104.5, 105, 103.8, 104.2), C(104.2, 105.5, 104, 105),
        C(105, 105.5, 104.5, 105.2),
    ]
    r = OpeningRangeDynamics().analyze(bars)
    assert r.status == "OPENING_RANGE_BREAKOUT_RETEST"
    assert r.retest


def test_failed_breakout_sets_reversal_watch():
    bars = [
        C(100, 102, 99, 101), C(101, 103, 100, 102), C(102, 104, 101, 103),
        C(103, 105, 103, 104.5), C(104.5, 105, 102, 103), C(103, 104, 102, 102.5),
    ]
    r = OpeningRangeDynamics().analyze(bars)
    assert r.status == "OPENING_RANGE_FAILED_BREAKOUT"
    assert r.reversal_watch


def test_forming_candle_cannot_confirm_breakout():
    base = [
        C(100, 102, 99, 101), C(101, 103, 100, 102), C(102, 104, 101, 103),
        C(103, 104, 102, 103), C(103, 104, 102, 103),
    ]
    quiet_forming = C(103, 104, 102, 103)
    explosive_forming = C(103, 110, 103, 109)
    a = OpeningRangeDynamics().analyze(base + [quiet_forming])
    b = OpeningRangeDynamics().analyze(base + [explosive_forming])
    assert a.to_dict() == b.to_dict()
