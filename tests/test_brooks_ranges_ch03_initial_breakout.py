from dataclasses import dataclass

from analysis.price_action.initial_breakout_dynamics import InitialBreakoutDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def test_initial_breakout_buy_confirmed():
    candles = [
        c(100, 101, 99, 100.5),
        c(100.5, 102, 100, 101),
        c(101, 102.5, 100.5, 101.5),
        c(101.5, 103, 101, 102),
        c(102, 103.5, 101.5, 102.5),
        c(102.5, 104, 102, 103),
        c(103, 104.5, 102.5, 103.5),
        c(103.5, 105, 103, 104),
        c(104, 108, 103.8, 107.7),
        c(107.7, 110, 107.5, 109.7),
        c(109.7, 112, 109.5, 111.8),
        c(111.8, 112.2, 111.2, 111.6),  # atual, ignorado
    ]

    r = InitialBreakoutDynamics().analisar(candles)

    assert r.valid is True
    assert r.direction == "BUY"
    assert r.state == "INITIAL_BREAKOUT_CONFIRMED"
    assert r.follow_through_bars >= 2
    assert r.acceptance_beyond_level is True


def test_initial_breakout_sell_confirmed():
    candles = [
        c(110, 111, 109, 109.5),
        c(109.5, 110, 108, 109),
        c(109, 109.5, 107.5, 108.5),
        c(108.5, 109, 107, 108),
        c(108, 108.5, 106.5, 107.5),
        c(107.5, 108, 106, 107),
        c(107, 107.5, 105.5, 106.5),
        c(106.5, 107, 105, 106),
        c(106, 106.2, 101, 101.3),
        c(101.3, 101.5, 98.5, 98.8),
        c(98.8, 99, 96.5, 96.7),
        c(96.7, 97.5, 96.2, 97.2),  # atual, ignorado
    ]

    r = InitialBreakoutDynamics().analisar(candles)

    assert r.valid is True
    assert r.direction == "SELL"
    assert r.state == "INITIAL_BREAKOUT_CONFIRMED"
    assert r.follow_through_bars >= 2


def test_initial_breakout_failure_risk_when_price_returns_to_range():
    candles = [
        c(100, 101, 99, 100),
        c(100, 102, 99.5, 101),
        c(101, 102.5, 100.5, 101.5),
        c(101.5, 103, 101, 102),
        c(102, 103.5, 101.5, 102.5),
        c(102.5, 104, 102, 103),
        c(103, 104.5, 102.5, 103.5),
        c(103.5, 105, 103, 104),
        c(104, 108, 103.8, 107),
        c(107, 107.3, 103.5, 104.2),
        c(104.2, 105, 103.8, 104.5),
        c(104.5, 110, 104, 109),  # atual, ignorado
    ]

    r = InitialBreakoutDynamics().analisar(candles)

    assert r.direction == "BUY"
    assert r.state == "INITIAL_BREAKOUT_FAILURE_RISK"
    assert r.rejection_to_range is True


def test_current_candle_cannot_create_initial_breakout():
    candles = [
        c(100, 101, 99, 100),
        c(100, 102, 99, 101),
        c(101, 103, 100, 102),
        c(102, 104, 101, 103),
        c(103, 105, 102, 104),
        c(104, 105, 103, 104),
        c(104, 105, 103, 104),
        c(104, 105, 103, 104),
        c(104, 105, 103, 104),
        c(104, 105, 103, 104),
        c(104, 112, 103.5, 111.5),  # atual
    ]

    r = InitialBreakoutDynamics().analisar(candles)

    assert r.valid is True
    assert r.state == "NO_BREAKOUT"


def test_insufficient_history():
    candles = [c(100, 101, 99, 100)] * 5
    r = InitialBreakoutDynamics().analisar(candles)
    assert r.valid is False
    assert "insufficient_history" in r.reasons
