from dataclasses import dataclass

from analysis.price_action.major_trend_reversal_dynamics import MajorTrendReversalDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_major_trend_reversal_buy_confirmed():
    candles = [
        C(110, 111, 108, 109), C(109, 110, 106, 107), C(107, 108, 104, 105),
        C(105, 106, 102, 103), C(103, 104, 100, 101), C(101, 103, 100, 102),
        C(102, 105, 101, 104), C(104, 108, 103, 107), C(107, 110, 106, 109),
        C(109, 111, 107, 108), C(108, 109, 105, 106), C(106, 108, 104, 107),
        C(107, 109, 106, 108), C(108, 110, 107, 109), C(109, 110, 108, 109),
        C(109, 110, 108, 109),  # current, excluded
    ]
    r = MajorTrendReversalDynamics().analyze(candles, "DOWN", structural_break_index=6)
    assert r.valid
    assert r.structural_break
    assert r.extreme_test
    assert r.second_attempt
    assert r.follow_through
    assert r.state == "MTR_CONFIRMED"
    assert r.reversal_direction == "BUY"


def test_major_trend_reversal_sell_confirmed():
    candles = [
        C(100, 102, 99, 101), C(101, 104, 100, 103), C(103, 106, 102, 105),
        C(105, 108, 104, 107), C(107, 110, 106, 109), C(109, 110, 107, 108),
        C(108, 109, 104, 105), C(105, 108, 104, 107), C(107, 110, 106, 109),
        C(109, 110, 107, 108), C(108, 109, 105, 106), C(106, 107, 103, 104),
        C(104, 105, 101, 102), C(102, 103, 100, 101), C(101, 102, 100, 101),
        C(101, 102, 100, 101),  # current, excluded
    ]
    r = MajorTrendReversalDynamics().analyze(candles, "UP", structural_break_index=6)
    assert r.valid
    assert r.structural_break
    assert r.extreme_test
    assert r.second_attempt
    assert r.follow_through
    assert r.state == "MTR_CONFIRMED"
    assert r.reversal_direction == "SELL"


def test_break_without_test_keeps_continuation_risk():
    candles = [C(100+i, 102+i, 99+i, 101+i) for i in range(12)]
    candles += [C(110, 111, 105, 106), C(106, 107, 103, 104), C(104, 105, 102, 103)]
    candles += [C(103, 104, 102, 103)]
    r = MajorTrendReversalDynamics().analyze(candles, "UP", structural_break_index=10)
    assert r.valid
    assert r.structural_break
    assert not r.follow_through
    assert r.old_trend_continuation_risk


def test_current_candle_cannot_complete_reversal():
    candles = [
        C(110,111,108,109), C(109,110,106,107), C(107,108,104,105), C(105,106,102,103),
        C(103,104,100,101), C(101,103,100,102), C(102,105,101,104), C(104,108,103,107),
        C(107,110,106,109), C(109,111,107,108), C(108,109,105,106), C(106,107,104,105),
        C(105,106,103,104), C(104,105,103,104),
        C(104,110,103,109),  # current only; would be misleading if included
    ]
    r = MajorTrendReversalDynamics().analyze(candles, "DOWN", structural_break_index=6)
    assert r.state != "MTR_CONFIRMED"


def test_invalid_trend_and_insufficient_history():
    engine = MajorTrendReversalDynamics()
    assert engine.analyze([], "SIDEWAYS").reason == "INVALID_OLD_TREND"
    short = [C(1,2,0,1) for _ in range(5)]
    assert engine.analyze(short, "UP").reason == "INSUFFICIENT_HISTORY"
