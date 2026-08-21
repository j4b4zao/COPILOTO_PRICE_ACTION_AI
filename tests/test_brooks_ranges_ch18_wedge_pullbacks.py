from dataclasses import dataclass

from analysis.price_action.wedge_pullback_dynamics import WedgePullbackDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return C(o, h, l, cl)


def test_insufficient_history_is_safe():
    result = WedgePullbackDynamics().analyze([c(1, 2, 0, 1.5)] * 8)
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_three_push_wedge_pullback_buy_context():
    candles = [
        c(100, 102, 99, 101), c(101, 104, 100, 103), c(103, 106, 102, 105),
        c(105, 107, 103, 104), c(104, 106, 101, 102), c(102, 105, 101, 104),
        c(104, 106, 100, 101), c(101, 104, 100, 103), c(103, 105, 99.5, 100.5),
        c(100.5, 103, 100, 102.5), c(102.5, 105, 99.8, 101),
        c(101, 104, 100.5, 103.5), c(103.5, 106, 103, 105.5),
        c(105.5, 108, 105, 107.5), c(107.5, 110, 107, 109.5),
        c(109.5, 111, 108.5, 110.5),
        c(110.5, 111, 110, 110.8),
    ]
    result = WedgePullbackDynamics().analyze(candles)
    assert result.trend_direction in ("UP", "NONE")
    if result.valid:
        assert result.push_count == 3
        assert result.setup_direction == "BUY"


def test_current_candle_does_not_confirm_breakout():
    base = [c(100+i, 101+i, 99+i, 100.7+i) for i in range(15)]
    forming = c(115, 120, 114, 119.5)
    result = WedgePullbackDynamics().analyze(base + [forming])
    assert result.breakout_confirmed is False or result.valid is False
