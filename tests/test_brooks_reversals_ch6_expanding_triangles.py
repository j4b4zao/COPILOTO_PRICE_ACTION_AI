from dataclasses import dataclass

from analysis.price_action.expanding_triangle_reversal_dynamics import (
    ExpandingTriangleReversalDynamics,
)


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_insufficient_history():
    candles = [C(10, 11, 9, 10.5) for _ in range(8)]
    result = ExpandingTriangleReversalDynamics().analyze(candles)
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_no_expanding_triangle_when_range_not_expanding():
    candles = [
        C(10, 10.5, 9.8, 10.2), C(10.2, 11, 10, 10.8), C(10.8, 11.5, 10.5, 11),
        C(11, 11.2, 9.5, 9.8), C(9.8, 10.3, 9.2, 10), C(10, 11.3, 9.8, 11),
        C(11, 11.6, 10.7, 11.2), C(11.2, 11.3, 9.4, 9.7), C(9.7, 10.2, 9.3, 10),
        C(10, 11.4, 9.8, 11.1), C(11.1, 11.5, 10.7, 11), C(11, 11.2, 9.5, 9.9),
        C(9.9, 10.3, 9.4, 10), C(10, 10.6, 9.7, 10.2), C(10.2, 10.5, 9.8, 10.1),
    ]
    result = ExpandingTriangleReversalDynamics().analyze(candles)
    assert result.state != "EXPANDING_TRIANGLE_REVERSAL_CONFIRMED"


def test_current_bar_cannot_confirm_reversal():
    candles = [
        C(10, 10.4, 9.8, 10.2), C(10.2, 11, 10, 10.8), C(10.8, 11.6, 10.5, 11),
        C(11, 11.1, 9.3, 9.6), C(9.6, 10, 8.9, 9.4), C(9.4, 11.4, 9.2, 11),
        C(11, 12, 10.7, 11.5), C(11.5, 11.7, 8.6, 9), C(9, 9.5, 8.2, 8.8),
        C(8.8, 12.3, 8.7, 11.9), C(11.9, 12.8, 11.6, 12.4), C(12.4, 12.9, 10.5, 11),
        C(11, 11.2, 8.0, 8.4), C(8.4, 9.2, 7.8, 8.9), C(8.9, 9.5, 8.3, 9.1),
        # current/in-formation: apparent upper-edge failed breakout, excluded
        C(9.1, 14.0, 8.9, 9.0),
    ]
    result = ExpandingTriangleReversalDynamics().analyze(candles)
    assert result.state != "EXPANDING_TRIANGLE_REVERSAL_CONFIRMED"


def test_result_schema_is_stable():
    candles = [C(10 + i * 0.1, 10.7 + i * 0.1, 9.5 + i * 0.05, 10.2 + i * 0.1) for i in range(16)]
    result = ExpandingTriangleReversalDynamics().analyze(candles)
    data = result.to_dict()
    assert "quality_score" in data
    assert "breakout_continuation_risk" in data
    assert "volatility_expansion" in data
