"""Tests for Brooks Trading Ranges chapter 8 diagnostics."""

from dataclasses import dataclass

from analysis.price_action.gap_range_measured_move_dynamics import (
    GapRangeMeasuredMoveDynamics,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def test_buy_gap_projects_measured_move_magnet():
    candles = [
        c(100.0, 100.8, 99.8, 100.5),
        c(100.5, 101.2, 100.3, 101.0),
        c(101.0, 101.7, 100.8, 101.5),
        c(101.5, 102.0, 101.2, 101.8),
        c(101.8, 102.4, 101.6, 102.2),
        c(103.0, 103.8, 102.8, 103.6),  # gap above 102.4
        c(103.6, 104.2, 103.4, 104.0),
        c(104.0, 104.5, 103.8, 104.3),
        c(104.3, 104.7, 104.0, 104.5),
        c(104.5, 104.8, 104.2, 104.6),  # forming; excluded
    ]

    result = GapRangeMeasuredMoveDynamics().analyze(candles)

    assert result.valid is True
    assert result.direction == "BUY"
    assert result.gap_target > result.gap_midpoint
    assert "GAP_MEASURED_MOVE" in result.reasons


def test_sell_gap_projects_downside_target():
    candles = [
        c(110.0, 110.2, 109.3, 109.5),
        c(109.5, 109.7, 108.8, 109.0),
        c(109.0, 109.2, 108.3, 108.5),
        c(108.5, 108.8, 107.9, 108.1),
        c(108.1, 108.4, 107.5, 107.8),
        c(106.9, 107.2, 106.2, 106.5),  # gap below 107.5
        c(106.5, 106.7, 105.8, 106.0),
        c(106.0, 106.2, 105.4, 105.7),
        c(105.7, 105.9, 105.1, 105.4),
        c(105.4, 105.7, 105.2, 105.5),
    ]

    result = GapRangeMeasuredMoveDynamics().analyze(candles)

    assert result.valid is True
    assert result.direction == "SELL"
    assert result.gap_target < result.gap_midpoint


def test_trading_range_breakout_projects_range_height():
    candles = [
        c(100.4, 101.2, 100.0, 100.8),
        c(100.8, 101.6, 100.2, 101.0),
        c(101.0, 101.8, 100.4, 101.2),
        c(101.2, 101.7, 100.3, 100.9),
        c(100.9, 101.9, 100.5, 101.5),
        c(101.5, 102.0, 100.6, 101.4),
        c(101.5, 102.8, 101.4, 102.6),  # breakout above 102.0
        c(102.6, 103.2, 102.3, 103.0),
        c(103.0, 103.5, 102.8, 103.3),
        c(103.3, 103.6, 103.0, 103.4),
    ]

    result = GapRangeMeasuredMoveDynamics().analyze(candles)

    assert result.valid is True
    assert result.range_target > result.range_breakout_level
    assert result.range_height > 0
    assert "TRADING_RANGE_MEASURED_MOVE" in result.reasons


def test_target_zone_flags_when_price_nears_projection():
    candles = [
        c(100.0, 100.8, 99.8, 100.5),
        c(100.5, 101.2, 100.3, 101.0),
        c(101.0, 101.7, 100.8, 101.5),
        c(101.5, 102.0, 101.2, 101.8),
        c(101.8, 102.4, 101.6, 102.2),
        c(103.0, 103.8, 102.8, 103.6),
        c(103.6, 104.8, 103.4, 104.6),
        c(104.6, 105.8, 104.4, 105.6),
        c(105.6, 106.6, 105.4, 106.4),
        c(106.4, 106.8, 106.1, 106.5),
    ]

    result = GapRangeMeasuredMoveDynamics().analyze(candles)

    assert result.valid is True
    assert result.progress_ratio >= 0.0
    assert result.state in {
        "TARGET_ACTIVE",
        "APPROACHING_TARGET",
        "TARGET_REACHED",
        "TARGET_OVERSHOT",
    }


def test_forming_candle_cannot_create_gap_or_breakout():
    candles = [
        c(100.0, 100.8, 99.7, 100.2),
        c(100.2, 100.9, 99.8, 100.4),
        c(100.4, 101.0, 100.0, 100.5),
        c(100.5, 101.1, 100.1, 100.6),
        c(100.6, 101.0, 100.2, 100.5),
        c(100.5, 101.1, 100.0, 100.4),
        c(100.4, 101.0, 100.1, 100.6),
        c(100.6, 101.1, 100.2, 100.5),
        c(100.5, 101.0, 100.1, 100.4),
        c(103.0, 104.0, 102.8, 103.8),  # forming only
    ]

    result = GapRangeMeasuredMoveDynamics().analyze(candles)

    assert result.valid is False
    assert "NO_MEASURED_MOVE_SOURCE" in result.reasons


def test_insufficient_history_is_rejected():
    candles = [c(100, 101, 99, 100.5)] * 5
    result = GapRangeMeasuredMoveDynamics().analyze(candles)
    assert result.valid is False
    assert result.reasons == ("INSUFFICIENT_HISTORY",)
