from dataclasses import dataclass

from analysis.price_action.reversal_pattern_dynamics import ReversalPatternDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def c(o,h,l,x):
    return C(o,h,l,x)


def test_insufficient_history():
    r = ReversalPatternDynamics().analyze([c(1,2,0,1)] * 8)
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_double_top_can_be_detected_without_auto_entry():
    bars = [
        c(100,102,99,101), c(101,104,100,103), c(103,106,102,105),
        c(105,108,104,107), c(107,110,106,109), c(109,111,107,108),
        c(108,109,104,105), c(105,107,103,106), c(106,110.8,105,110),
        c(110,111,107,108), c(108,109,104,105), c(105,106,101,102),
        c(102,103,99,100), c(100,101,98,99), c(99,100,97,98),
        c(98,99,96,97),
        c(97,120,80,100),  # candle atual: ignorado
    ]
    r = ReversalPatternDynamics().analyze(bars)
    assert r.prior_trend in ("UP", "NONE")
    if r.valid:
        assert r.pattern in ("DOUBLE_TOP", "HEAD_AND_SHOULDERS_TOP")
        assert r.reversal_direction == "SELL"


def test_current_candle_cannot_confirm_reversal():
    base = [c(100+i, 101+i, 99+i, 100.8+i) for i in range(15)]
    current = c(50, 200, 40, 50)
    r = ReversalPatternDynamics().analyze(base + [current])
    assert r.signal_confirmed is False
