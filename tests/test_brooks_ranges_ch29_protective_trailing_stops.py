"""Tests for Brooks Trading Ranges chapter 29 diagnostics."""

from dataclasses import dataclass

from analysis.price_action.protective_trailing_stop_dynamics import (
    ProtectiveTrailingStopDynamics,
)


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def buy_sequence():
    closed = [
        c(100, 104, 99, 103),
        c(103, 106, 101, 105),
        c(105, 110, 104, 108),  # prior swing high
        c(108, 107, 102, 104),
        c(104, 106, 100, 105),  # higher swing low / trail reference
        c(105, 108, 102, 107),
        c(107, 111, 105, 110),
        c(110, 115, 108, 113),  # new swing high
        c(113, 112, 106, 109),
        c(109, 111, 105, 108),
    ]
    return closed + [c(108, 120, 107, 119)]  # current/forming; excluded


def sell_sequence():
    closed = [
        c(120, 121, 116, 117),
        c(117, 119, 114, 115),
        c(115, 116, 110, 112),  # prior swing low
        c(112, 118, 111, 116),
        c(116, 120, 114, 115),  # lower swing high / trail reference
        c(115, 118, 112, 113),
        c(113, 115, 108, 109),
        c(109, 112, 104, 106),  # new swing low
        c(106, 111, 105, 108),
        c(108, 112, 106, 109),
    ]
    return closed + [c(109, 110, 90, 92)]  # current/forming; excluded


def test_buy_trailing_stop_advances_after_new_swing_high():
    result = ProtectiveTrailingStopDynamics().analyze(
        buy_sequence(),
        direction="BUY",
        entry_price=105,
        initial_stop=95,
        current_stop=95,
        tick_size=1,
    )

    assert result.valid is True
    assert result.state == "TRAILING_STOP_ADVANCE"
    assert result.structural_advance_confirmed is True
    assert result.proposed_stop == 99
    assert result.stop_improved is True


def test_sell_trailing_stop_advances_after_new_swing_low():
    result = ProtectiveTrailingStopDynamics().analyze(
        sell_sequence(),
        direction="SELL",
        entry_price=115,
        initial_stop=125,
        current_stop=125,
        tick_size=1,
    )

    assert result.valid is True
    assert result.state == "TRAILING_STOP_ADVANCE"
    assert result.structural_advance_confirmed is True
    assert result.proposed_stop == 121
    assert result.stop_improved is True


def test_stop_is_never_loosened():
    result = ProtectiveTrailingStopDynamics().analyze(
        buy_sequence(),
        direction="BUY",
        entry_price=105,
        initial_stop=95,
        current_stop=90,
        tick_size=1,
    )

    assert result.valid is True
    assert result.state == "STOP_LOOSENING_REJECTED"
    assert result.stop_loosened is True
    assert result.proposed_stop == 95


def test_current_candle_cannot_create_trailing_confirmation():
    candles = buy_sequence()
    # Remove the already confirmed new swing high. The remaining current candle
    # makes a huge high, but it must not be used because it is still forming.
    candles = candles[:7] + [candles[-1]]

    result = ProtectiveTrailingStopDynamics().analyze(
        candles,
        direction="BUY",
        entry_price=105,
        initial_stop=95,
        current_stop=95,
        tick_size=1,
    )

    assert result.valid is True
    assert result.structural_advance_confirmed is False
    assert result.state == "PROTECTIVE_STOP_HOLD"


def test_invalid_protective_stop_geometry_is_rejected():
    result = ProtectiveTrailingStopDynamics().analyze(
        buy_sequence(),
        direction="BUY",
        entry_price=105,
        initial_stop=110,
    )

    assert result.valid is False
    assert result.state == "INVALID_PROTECTIVE_STOP"


def test_insufficient_history():
    result = ProtectiveTrailingStopDynamics().analyze(
        [c(100, 101, 99, 100)] * 5,
        direction="BUY",
        entry_price=100,
        initial_stop=95,
    )

    assert result.valid is False
    assert result.reason == "INSUFFICIENT_HISTORY"
