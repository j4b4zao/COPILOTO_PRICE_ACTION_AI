from dataclasses import dataclass

from analysis.price_action.gap_dynamics import GapDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return C(o, h, l, cl)


def test_breakaway_gap_buy():
    bars = [
        c(100, 101, 99, 100.4), c(100.3, 101.2, 99.8, 100.1),
        c(100, 101, 99.7, 100.2), c(100.1, 101.1, 99.9, 100.0),
        c(100, 101, 99.8, 100.1), c(102.2, 103.5, 102.0, 103.2),
        c(103.2, 104.1, 102.8, 103.9), c(103.9, 104.8, 103.5, 104.5),
        c(104.5, 105.0, 104.0, 104.7), c(104.7, 105.2, 104.2, 104.9),
    ]
    r = GapDynamics().analyze(bars)
    assert r.valid
    assert r.direction == "BUY"
    assert r.gap_type in {"BREAKAWAY_GAP", "UNCLASSIFIED_GAP"}
    assert not r.filled


def test_measuring_gap_buy_has_target():
    bars = [
        c(100, 101, 99.8, 100.8), c(100.8, 102, 100.5, 101.8),
        c(101.8, 103, 101.5, 102.8), c(102.8, 104, 102.4, 103.7),
        c(103.7, 104.8, 103.2, 104.4), c(105.6, 106.8, 105.4, 106.5),
        c(106.5, 107.4, 106.0, 107.1), c(107.1, 108.0, 106.8, 107.8),
        c(107.8, 108.5, 107.3, 108.2), c(108.2, 108.8, 107.9, 108.5),
    ]
    r = GapDynamics().analyze(bars)
    assert r.valid
    assert r.direction == "BUY"
    assert r.gap_type == "MEASURING_GAP"
    assert r.measuring_target > r.gap_mid


def test_exhaustion_gap_buy_when_gap_fills():
    bars = [
        c(100, 101, 99.8, 100.8), c(100.8, 102, 100.5, 101.8),
        c(101.8, 103, 101.5, 102.8), c(102.8, 104, 102.4, 103.7),
        c(103.7, 104.8, 103.2, 104.4), c(105.6, 106.8, 105.4, 106.5),
        c(106.5, 106.8, 104.6, 104.9), c(104.9, 105.2, 103.9, 104.2),
        c(104.2, 104.8, 103.8, 104.0), c(104.0, 104.5, 103.6, 103.9),
    ]
    r = GapDynamics().analyze(bars)
    assert r.valid
    assert r.filled
    assert r.gap_type in {"EXHAUSTION_GAP", "COMMON_GAP"}


def test_sell_gap_supported():
    bars = [
        c(110, 109.5, 108.8, 109.0), c(109, 108.8, 107.8, 108.0),
        c(108, 107.7, 106.8, 107.0), c(107, 106.8, 105.8, 106.0),
        c(106, 105.8, 104.8, 105.0), c(103.8, 103.9, 102.5, 102.8),
        c(102.8, 102.9, 101.8, 102.0), c(102, 102.1, 101.0, 101.2),
        c(101.2, 101.5, 100.7, 101.0), c(101.0, 101.2, 100.6, 100.9),
    ]
    r = GapDynamics().analyze(bars)
    assert r.valid
    assert r.direction == "SELL"


def test_current_candle_is_excluded():
    bars = [
        c(100, 101, 99, 100), c(100, 101, 99, 100), c(100, 101, 99, 100),
        c(100, 101, 99, 100), c(100, 101, 99, 100), c(100, 101, 99, 100),
        c(100, 101, 99, 100), c(100, 101, 99, 100), c(103, 104, 102, 103.5),
    ]
    r = GapDynamics().analyze(bars)
    assert not r.valid
    assert "NO_GAP" in r.reasons


def test_insufficient_history():
    r = GapDynamics().analyze([c(100, 101, 99, 100)] * 5)
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons
