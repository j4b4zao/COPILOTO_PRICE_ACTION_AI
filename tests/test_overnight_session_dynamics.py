from dataclasses import dataclass

from analysis.price_action.overnight_session_dynamics import OvernightSessionDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def _c(o, h, l, c):
    return Candle(o, h, l, c)


def _overnight_with_current():
    return [
        _c(100, 102, 99, 101),
        _c(101, 104, 100, 103),
        _c(103, 105, 101, 104),
        _c(104, 106, 103, 105),
        _c(105, 110, 90, 109),  # current: must be ignored
    ]


def test_insufficient_overnight_history():
    result = OvernightSessionDynamics().analyze([_c(1, 2, 0, 1)])
    assert result.valid is False
    assert "INSUFFICIENT_OVERNIGHT_HISTORY" in result.reasons


def test_levels_ready_without_regular_session():
    result = OvernightSessionDynamics().analyze(_overnight_with_current())
    assert result.valid is True
    assert result.status == "OVERNIGHT_LEVELS_READY"
    assert result.overnight_high == 106
    assert result.overnight_low == 99


def test_regular_session_high_rejection():
    regular = [
        _c(103, 107, 102, 104),  # reject above overnight high 106
        _c(104, 105, 101, 102),
        _c(102, 120, 80, 119),   # current ignored
    ]
    result = OvernightSessionDynamics().analyze(
        _overnight_with_current(), regular, tick_size=0.25
    )
    assert result.status == "OVERNIGHT_HIGH_REJECTION"
    assert result.level_signal == "SELL_REJECTION"
    assert result.overnight_high_rejected is True
    assert result.breakout_confirmed is False


def test_regular_session_low_rejection():
    regular = [
        _c(101, 102, 98, 100),
        _c(100, 103, 99, 102),
        _c(102, 120, 80, 119),  # current ignored
    ]
    result = OvernightSessionDynamics().analyze(
        _overnight_with_current(), regular, tick_size=0.25
    )
    assert result.status == "OVERNIGHT_LOW_REJECTION"
    assert result.level_signal == "BUY_REJECTION"
    assert result.overnight_low_rejected is True


def test_high_breakout_requires_follow_through():
    regular = [
        _c(105, 108, 104, 107),
        _c(107, 109, 106, 108),
        _c(108, 120, 80, 90),  # current ignored
    ]
    result = OvernightSessionDynamics().analyze(
        _overnight_with_current(), regular, tick_size=0.25
    )
    assert result.status == "OVERNIGHT_HIGH_BREAKOUT_CONFIRMED"
    assert result.level_signal == "BUY_BREAKOUT"
    assert result.follow_through is True
    assert result.breakout_confirmed is True


def test_single_breakout_close_waits_for_follow_through():
    regular = [
        _c(105, 108, 104, 107),
        _c(107, 120, 80, 90),  # current ignored
    ]
    result = OvernightSessionDynamics().analyze(
        _overnight_with_current(), regular, tick_size=0.25
    )
    assert result.status == "OVERNIGHT_BREAKOUT_ATTEMPT"
    assert result.breakout_confirmed is False


def test_current_candle_cannot_create_breakout_or_rejection():
    regular = [
        _c(102, 104, 101, 103),
        _c(103, 104, 102, 103),
        _c(103, 120, 80, 119),  # current ignored entirely
    ]
    result = OvernightSessionDynamics().analyze(
        _overnight_with_current(), regular, tick_size=0.25
    )
    assert result.overnight_high_breakout is False
    assert result.overnight_low_breakout is False
    assert result.overnight_high_rejected is False
    assert result.overnight_low_rejected is False
