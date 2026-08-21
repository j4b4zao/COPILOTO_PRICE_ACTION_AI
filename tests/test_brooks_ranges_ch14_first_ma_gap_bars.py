from dataclasses import dataclass

from analysis.price_action.first_ma_gap_bar_dynamics import FirstMAGapBarDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(o, h, l, cl):
    return Candle(o, h, l, cl)


def bull_history(reaction=True):
    bars = []
    price = 100.0
    for _ in range(24):
        bars.append(c(price, price + 2.4, price - 0.4, price + 2.0))
        price += 2.0

    # Deep pullback reaches/crosses the EMA.
    bars += [
        c(148.0, 148.5, 138.0, 140.0),
        c(140.0, 141.0, 132.0, 134.0),
        # First bar completely below the EMA.
        c(133.0, 133.5, 129.0, 131.0),
    ]

    if reaction:
        bars += [
            c(131.0, 137.0, 130.5, 136.0),
            c(136.0, 140.0, 135.0, 139.0),
        ]

    # Current/forming candle, excluded by the engine.
    bars.append(c(139.0, 141.0, 138.0, 140.0))
    return bars


def bear_history(reaction=True):
    bars = []
    price = 200.0
    for _ in range(24):
        bars.append(c(price, price + 0.4, price - 2.4, price - 2.0))
        price -= 2.0

    bars += [
        c(152.0, 162.0, 151.5, 160.0),
        c(160.0, 168.0, 159.0, 166.0),
        # First bar completely above the EMA.
        c(167.0, 171.0, 166.5, 169.0),
    ]

    if reaction:
        bars += [
            c(169.0, 169.5, 162.0, 163.0),
            c(163.0, 164.0, 158.0, 159.0),
        ]

    bars.append(c(159.0, 160.0, 157.0, 158.0))
    return bars


def test_bull_first_ma_gap_bar_reaction_is_confirmed():
    result = FirstMAGapBarDynamics().analyze(bull_history())
    assert result.valid is True
    assert result.trend_direction == "UP"
    assert result.gap_bar_side == "BELOW_EMA"
    assert result.reaction_confirmed is True
    assert result.continuation_bias is True
    assert result.reversal_risk is False
    assert result.state == "FIRST_MA_GAP_REACTION_CONFIRMED"


def test_bear_first_ma_gap_bar_reaction_is_confirmed():
    result = FirstMAGapBarDynamics().analyze(bear_history())
    assert result.valid is True
    assert result.trend_direction == "DOWN"
    assert result.gap_bar_side == "ABOVE_EMA"
    assert result.reaction_confirmed is True
    assert result.continuation_bias is True
    assert result.reversal_risk is False


def test_first_ma_gap_bar_without_follow_through_waits():
    result = FirstMAGapBarDynamics().analyze(bull_history(reaction=False))
    assert result.valid is True
    assert result.reaction_confirmed is False
    assert result.continuation_bias is False
    assert result.state == "FIRST_MA_GAP_BAR"


def test_failed_bull_signal_marks_reversal_risk():
    bars = bull_history(reaction=False)[:-1]
    # Closed bar after the gap continues sharply down instead of reacting up.
    bars.append(c(131.0, 132.0, 124.0, 125.0))
    bars.append(c(125.0, 126.0, 122.0, 123.0))
    bars.append(c(123.0, 124.0, 121.0, 122.0))  # current
    result = FirstMAGapBarDynamics().analyze(bars)
    assert result.valid is True
    assert result.failed_signal is True
    assert result.reversal_risk is True
    assert result.continuation_bias is False
    assert result.state == "FIRST_MA_GAP_SIGNAL_FAILED"


def test_current_candle_cannot_create_first_ma_gap_bar():
    bars = bull_history(reaction=False)
    # Remove the real closed gap bar and make only the current candle a gap bar.
    bars = bars[:26]
    bars.append(c(133.0, 133.5, 129.0, 131.0))  # current only
    result = FirstMAGapBarDynamics().analyze(bars)
    assert result.valid is False
    assert "NO_FIRST_MA_GAP_BAR" in result.reasons


def test_insufficient_history_is_rejected():
    bars = [c(100, 101, 99, 100.5) for _ in range(10)]
    result = FirstMAGapBarDynamics().analyze(bars)
    assert result.valid is False
    assert result.reasons == ("INSUFFICIENT_HISTORY",)
