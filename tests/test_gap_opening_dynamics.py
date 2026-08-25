from dataclasses import dataclass

from analysis.price_action.gap_opening_dynamics import GapOpeningDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_large_gap_up_continuation_sets_trend_day_watch():
    bars = [
        C(110, 113, 109, 112), C(112, 115, 111, 114), C(114, 117, 113, 116),
        C(116, 118, 115, 117), C(117, 119, 116, 118), C(118, 119, 117, 118),
    ]
    r = GapOpeningDynamics().analyze(previous_close=100, session_candles=bars, reference_range=16)
    assert r.valid
    assert r.direction == "BUY"
    assert r.status == "GAP_CONTINUATION_CONFIRMED"
    assert r.trend_day_watch


def test_gap_up_fill_and_reversal():
    bars = [
        C(110, 111, 106, 108), C(108, 109, 102, 104), C(104, 105, 99, 100),
        C(100, 101, 97, 98), C(98, 100, 97, 99), C(99, 100, 98, 99),
    ]
    r = GapOpeningDynamics().analyze(previous_close=100, session_candles=bars, reference_range=20)
    assert r.gap_fill
    assert r.reversal
    assert r.status == "GAP_REVERSAL_CONFIRMED"


def test_two_sided_gap_opening_can_remain_range():
    bars = [
        C(110, 113, 108, 112), C(112, 113, 108, 109), C(109, 112, 108, 111),
        C(111, 112, 108, 109), C(109, 112, 108, 111), C(111, 112, 109, 110),
    ]
    r = GapOpeningDynamics().analyze(previous_close=100, session_candles=bars, reference_range=30)
    assert r.early_two_sided
    assert r.status == "GAP_OPENING_TRADING_RANGE"
    assert r.trading_range_risk


def test_forming_candle_is_ignored():
    closed = [
        C(110, 113, 109, 112), C(112, 115, 111, 114), C(114, 117, 113, 116), C(116, 118, 115, 117)
    ]
    a = GapOpeningDynamics().analyze(previous_close=100, session_candles=closed + [C(117, 118, 116, 117)], reference_range=16)
    b = GapOpeningDynamics().analyze(previous_close=100, session_candles=closed + [C(117, 140, 90, 95)], reference_range=16)
    assert a.to_dict() == b.to_dict()


def test_invalid_context():
    r = GapOpeningDynamics().analyze(previous_close=0, session_candles=[], reference_range=0)
    assert not r.valid
