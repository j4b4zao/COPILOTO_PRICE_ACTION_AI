from dataclasses import dataclass

from analysis.price_action.failed_reversal_magnet_dynamics import (
    FailedReversalMagnetDynamics,
)


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_failed_bull_reversal_in_bear_trend_creates_resistance_magnet():
    candles = [
        C(110, 111, 108, 109),
        C(109, 110, 106, 107),
        C(107, 108, 104, 105),
        C(105, 106, 102, 103),
        C(103, 104, 100, 101),
        # bullish reversal attempt that fails
        C(101, 104, 99, 103),
        C(103, 103.5, 98, 99),
        C(99, 100, 96, 97),
        C(97, 99, 95, 96),
        C(96, 101, 95, 100),
        C(100, 103.5, 99, 103),
        C(103, 104.2, 102, 103.5),
        # forming candle excluded
        C(103.5, 106, 103, 105),
    ]

    result = FailedReversalMagnetDynamics().analyze(candles)

    assert result.valid is True
    assert result.trend_direction == "DOWN"
    assert result.signal_type == "FAILED_BULL_REVERSAL"
    assert result.support_resistance_role == "RESISTANCE"
    assert result.magnet_price == 104


def test_failed_bear_reversal_in_bull_trend_creates_support_magnet():
    candles = [
        C(90, 92, 89, 91),
        C(91, 94, 90, 93),
        C(93, 96, 92, 95),
        C(95, 98, 94, 97),
        C(97, 100, 96, 99),
        # bearish reversal attempt that fails
        C(99, 101, 96, 97),
        C(97, 102, 97, 101),
        C(101, 104, 100, 103),
        C(103, 105, 102, 104),
        C(104, 105, 98, 99),
        C(99, 100, 96.2, 97),
        C(97, 99, 96, 98),
        # forming candle excluded
        C(98, 99, 94, 95),
    ]

    result = FailedReversalMagnetDynamics().analyze(candles)

    assert result.valid is True
    assert result.trend_direction == "UP"
    assert result.signal_type == "FAILED_BEAR_REVERSAL"
    assert result.support_resistance_role == "SUPPORT"
    assert result.magnet_price == 96


def test_current_candle_is_not_used_to_create_signal():
    base = [
        C(100, 101, 99, 100),
        C(100, 102, 99, 101),
        C(101, 103, 100, 102),
        C(102, 104, 101, 103),
        C(103, 105, 102, 104),
        C(104, 106, 103, 105),
        C(105, 107, 104, 106),
        C(106, 108, 105, 107),
        C(107, 109, 106, 108),
        C(108, 110, 107, 109),
    ]
    forming = C(109, 115, 100, 101)

    result = FailedReversalMagnetDynamics().analyze(base + [forming])

    assert result.signal_bar_index != len(base)


def test_insufficient_history():
    candles = [C(1, 2, 0, 1)] * 6
    result = FailedReversalMagnetDynamics().analyze(candles)

    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
