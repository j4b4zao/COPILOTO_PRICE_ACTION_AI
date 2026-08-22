from dataclasses import dataclass

from analysis.price_action.wedge_reversal_dynamics import WedgeReversalDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return C(o, h, l, cl)


def test_insufficient_history():
    r = WedgeReversalDynamics().analyze([c(1, 2, 0, 1)] * 8, old_trend="UP")
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_three_push_pattern_does_not_confirm_without_break_and_followthrough():
    candles = [
        c(100, 101, 99, 100.5), c(100.5, 102, 100, 101.5),
        c(101.5, 103, 101, 102.5), c(102.5, 104, 102, 103.5),
        c(103.5, 105, 103, 104.5), c(104.5, 104.8, 102.5, 103),
        c(103, 106, 102.8, 105.5), c(105.5, 105.8, 103.8, 104.2),
        c(104.2, 106.8, 104, 106.2), c(106.2, 106.5, 104.8, 105.1),
        c(105.1, 107.2, 105, 106.7), c(106.7, 106.9, 105.8, 106),
        c(106, 107.4, 105.9, 107), c(107, 107.2, 106.4, 106.8),
        c(106.8, 107.3, 106.5, 107), c(107, 107.1, 106.7, 106.9),
        c(106.9, 107, 106.6, 106.8),
    ]
    r = WedgeReversalDynamics().analyze(candles, old_trend="UP", structural_break=False)
    assert r.reversal_confirmed is False
    assert r.old_trend_continuation_risk is True


def test_confirmed_wedge_reversal_sell_with_external_structural_break():
    candles = [
        c(100, 101, 99, 100.5), c(100.5, 102, 100, 101.5),
        c(101.5, 103.2, 101, 102.8), c(102.8, 101.8, 100.8, 101.2),
        c(101.2, 104.2, 101, 103.8), c(103.8, 102.8, 101.8, 102.2),
        c(102.2, 104.8, 102, 104.4), c(104.4, 103.6, 102.8, 103.1),
        c(103.1, 105.1, 103, 104.8), c(104.8, 104, 103.2, 103.5),
        c(103.5, 105.3, 103.4, 105), c(105, 104.6, 103.8, 104.1),
        c(104.1, 105.4, 104, 105.1), c(105.1, 104.2, 102.8, 103.1),
        c(103.1, 103.4, 101.5, 101.9), c(101.9, 102, 100.8, 101.1),
        c(101.1, 101.5, 100.9, 101.3),  # current candle excluded
    ]
    r = WedgeReversalDynamics().analyze(candles, old_trend="UP", structural_break=True)
    assert r.old_trend == "UP"
    assert r.reversal_direction == "SELL"
    assert r.reversal_confirmed is True
    assert r.state == "WEDGE_REVERSAL_CONFIRMED"
    assert r.old_trend_continuation_risk is False


def test_current_candle_cannot_confirm_reversal():
    candles = [c(100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(16)]
    candles += [c(116, 117, 115, 116.5), c(116.5, 117, 110, 110.5)]
    r = WedgeReversalDynamics().analyze(candles, old_trend="UP", structural_break=True)
    assert r.reversal_confirmed is False


def test_invalid_old_trend():
    candles = [c(1, 2, 0, 1.5)] * 20
    r = WedgeReversalDynamics().analyze(candles, old_trend="SIDEWAYS")
    assert r.valid is False
    assert "NO_CLEAR_OLD_TREND" in r.reasons
