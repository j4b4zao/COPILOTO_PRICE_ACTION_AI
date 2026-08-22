from dataclasses import dataclass

from analysis.price_action.climactic_reversal_dynamics import ClimacticReversalDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def test_buy_climax_then_bear_spike_and_follow_through_confirms_sell():
    candles = [
        c(100, 102, 99, 101), c(101, 103, 100, 102), c(102, 104, 101, 103),
        c(103, 105, 102, 104), c(104, 106, 103, 105),
        c(105, 112, 104.5, 111.5),
        c(111.5, 112, 105, 106),
        c(106, 106.5, 101, 102),
        c(102, 103, 100, 101),
        c(101, 102, 100, 101),  # current/forming
    ]
    r = ClimacticReversalDynamics().analyze(candles, "UP", structural_break=True)
    assert r.climax_detected
    assert r.opposite_spike
    assert r.follow_through
    assert r.reversal_direction == "SELL"
    assert r.state == "CLIMACTIC_REVERSAL_CONFIRMED"


def test_sell_climax_then_bull_spike_can_confirm_buy():
    candles = [
        c(110, 111, 108, 109), c(109, 110, 107, 108), c(108, 109, 106, 107),
        c(107, 108, 105, 106), c(106, 107, 104, 105),
        c(105, 105.5, 98, 98.5),
        c(98.5, 105, 98, 104.5),
        c(104.5, 109, 104, 108.5),
        c(108.5, 110, 108, 109.5),
        c(109.5, 110, 109, 109.5),
    ]
    r = ClimacticReversalDynamics().analyze(candles, "DOWN")
    assert r.climax_detected
    assert r.opposite_spike
    assert r.reversal_direction == "BUY"


def test_climax_without_opposite_spike_remains_wait():
    candles = [
        c(100, 102, 99, 101), c(101, 103, 100, 102), c(102, 104, 101, 103),
        c(103, 105, 102, 104), c(104, 106, 103, 105),
        c(105, 112, 104.5, 111.5),
        c(111.5, 112, 110, 111), c(111, 112, 110.5, 111.5),
        c(111.5, 112, 111, 111.8), c(111.8, 112, 111, 111.5),
    ]
    r = ClimacticReversalDynamics().analyze(candles, "UP")
    assert r.climax_detected
    assert not r.opposite_spike
    assert r.state == "CLIMAX_PAUSE_WAIT"
    assert r.continuation_risk


def test_current_candle_alone_cannot_create_opposite_spike():
    candles = [
        c(100, 102, 99, 101), c(101, 103, 100, 102), c(102, 104, 101, 103),
        c(103, 105, 102, 104), c(104, 106, 103, 105),
        c(105, 112, 104.5, 111.5),
        c(111.5, 112, 110.5, 111), c(111, 112, 110.5, 111.2),
        c(111.2, 112, 110.5, 111),
        c(111, 111.2, 103, 104),  # current/forming; excluded
    ]
    r = ClimacticReversalDynamics().analyze(candles, "UP")
    assert r.climax_detected
    assert not r.opposite_spike


def test_invalid_old_trend_and_insufficient_history():
    engine = ClimacticReversalDynamics()
    assert engine.analyze([], "SIDEWAYS").reason == "INVALID_OLD_TREND"
    short = [c(1, 2, 0, 1.5)] * 5
    assert engine.analyze(short, "UP").reason == "INSUFFICIENT_HISTORY"
