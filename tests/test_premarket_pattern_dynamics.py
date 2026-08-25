from dataclasses import dataclass

from analysis.price_action.premarket_pattern_dynamics import PremarketPatternDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def pm_base():
    return [
        C(100, 101, 99, 100.5),
        C(100.5, 102, 100, 101.5),
        C(101.5, 103, 101, 102.5),
        C(102.5, 104, 102, 103.0),
        C(103.0, 103.5, 102.5, 103.2),  # current/incomplete
    ]


def test_insufficient_history():
    r = PremarketPatternDynamics().analyze([C(1, 2, 0, 1)], [C(1, 2, 0, 1)])
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_premarket_high_rejection():
    regular = [
        C(103, 104.5, 102.8, 103.5),
        C(103.5, 104.2, 102.8, 103.0),
        C(103.0, 103.2, 101.8, 102.0),
        C(102.0, 108.0, 101.5, 107.0),  # current ignored
    ]
    r = PremarketPatternDynamics().analyze(pm_base(), regular)
    assert r.valid
    assert r.high_rejected
    assert r.status == "PREMARKET_HIGH_REJECTION"
    assert r.reversal_watch


def test_premarket_low_rejection():
    regular = [
        C(100.5, 101.0, 98.5, 99.5),
        C(99.5, 100.5, 98.8, 100.2),
        C(100.2, 101.5, 99.8, 101.2),
        C(101.2, 95.0, 94.0, 95.0),  # current ignored
    ]
    r = PremarketPatternDynamics().analyze(pm_base(), regular)
    assert r.low_rejected
    assert r.status == "PREMARKET_LOW_REJECTION"


def test_high_breakout_requires_follow_through():
    regular = [
        C(103.5, 104.8, 103.0, 104.5),
        C(104.5, 105.5, 104.2, 105.2),
        C(105.2, 106.0, 105.0, 105.8),
        C(105.8, 110.0, 105.0, 109.0),  # current ignored
    ]
    r = PremarketPatternDynamics().analyze(pm_base(), regular)
    assert r.high_breakout_confirmed
    assert r.status == "PREMARKET_HIGH_BREAKOUT_CONFIRMED"
    assert r.breakout_watch


def test_single_breakout_close_is_only_context_not_confirmation():
    regular = [
        C(103.0, 103.8, 102.5, 103.4),
        C(103.4, 104.6, 103.2, 104.3),
        C(104.3, 104.5, 103.8, 104.0),
        C(104.0, 110.0, 103.0, 109.0),  # current ignored
    ]
    r = PremarketPatternDynamics().analyze(pm_base(), regular)
    assert not r.high_breakout_confirmed


def test_gap_close_momentum_can_override_ma_conflict_diagnostically():
    regular = [
        C(97.0, 98.0, 96.8, 97.8),
        C(97.8, 99.0, 97.5, 98.8),
        C(98.8, 100.0, 98.5, 99.8),
        C(99.8, 120.0, 90.0, 110.0),  # current ignored
    ]
    r = PremarketPatternDynamics().analyze(
        pm_base(), regular, regular_ma=98.0, extended_ma=103.0
    )
    assert r.gap_direction == "DOWN"
    assert r.gap_closing_momentum
    assert r.moving_average_conflict
    assert r.momentum_over_ma


def test_current_candle_cannot_create_rejection_or_breakout():
    regular = [
        C(102.0, 103.0, 101.5, 102.5),
        C(102.5, 103.2, 102.0, 102.8),
        C(102.8, 103.5, 102.2, 103.0),
        C(103.0, 110.0, 90.0, 91.0),  # current/incomplete
    ]
    r = PremarketPatternDynamics().analyze(pm_base(), regular)
    assert not r.high_rejected
    assert not r.low_rejected
    assert not r.high_breakout_confirmed
    assert not r.low_breakout_confirmed
