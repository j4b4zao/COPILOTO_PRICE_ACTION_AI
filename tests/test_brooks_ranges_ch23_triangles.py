from dataclasses import dataclass

from analysis.price_action.triangle_dynamics import TriangleDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_insufficient_history():
    candles = [C(1, 2, 0, 1.5) for _ in range(8)]
    result = TriangleDynamics().analyze(candles)
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_triangle_breakout_mode_without_directional_bias():
    candles = [
        C(100, 101, 99, 100),
        C(100, 110, 100, 105),
        C(105, 106, 96, 100),
        C(100, 108, 99, 104),
        C(104, 105, 97, 101),
        C(101, 106, 99, 103),
        C(103, 104, 98, 101),
        C(101, 105, 100, 103),
        C(103, 104, 99, 101),
        C(101, 103, 100, 102),
        C(102, 103, 100.5, 101.5),
        C(101.5, 102.5, 100.8, 101.8),
        C(101.8, 102.2, 101, 101.6),
        C(101.6, 102, 101.1, 101.7),
        C(101.7, 101.9, 101.2, 101.6),
        C(101.6, 101.8, 101.3, 101.55),
        C(101.55, 101.7, 101.35, 101.5),
        C(101.5, 101.6, 101.4, 101.5),
    ]
    result = TriangleDynamics().analyze(candles)
    assert result.valid is True
    assert result.breakout_mode is True
    assert result.direction == "NONE"


def test_current_candle_cannot_confirm_breakout():
    base = [
        C(100, 101, 99, 100), C(100, 110, 100, 105), C(105, 106, 96, 100),
        C(100, 108, 99, 104), C(104, 105, 97, 101), C(101, 106, 99, 103),
        C(103, 104, 98, 101), C(101, 105, 100, 103), C(103, 104, 99, 101),
        C(101, 103, 100, 102), C(102, 103, 100.5, 101.5), C(101.5, 102.5, 100.8, 101.8),
        C(101.8, 102.2, 101, 101.6), C(101.6, 102, 101.1, 101.7), C(101.7, 101.9, 101.2, 101.6),
        C(101.6, 101.8, 101.3, 101.55), C(101.55, 101.7, 101.35, 101.5),
    ]
    current = C(101.5, 110, 101.4, 109)
    result = TriangleDynamics().analyze(base + [current])
    assert result.breakout_confirmed is False
