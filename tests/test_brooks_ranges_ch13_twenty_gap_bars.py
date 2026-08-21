from dataclasses import dataclass

from analysis.price_action.twenty_gap_bars_dynamics import TwentyGapBarsDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def _bull_sequence(include_touch=True, current_touch=False):
    candles = []
    price = 100.0

    # Build enough history for EMA warm-up and then >20 bars clearly above it.
    for _ in range(8):
        candles.append(Candle(price, price + 0.4, price - 0.4, price + 0.1))
        price += 0.1

    for _ in range(22):
        price += 1.0
        candles.append(Candle(price - 0.2, price + 0.5, price - 0.35, price + 0.25))

    if include_touch and not current_touch:
        # Pullback reaches/briefly crosses the EMA, then bullish reaction.
        candles.append(Candle(price + 0.2, price + 0.3, price - 8.5, price - 6.5))
        candles.append(Candle(price - 6.5, price - 3.5, price - 7.0, price - 4.0))
        candles.append(Candle(price - 4.0, price - 1.0, price - 4.3, price - 1.5))

    # Current/forming candle: excluded from confirmation.
    if current_touch:
        candles.append(Candle(price, price + 0.2, price - 9.0, price - 7.0))
    else:
        candles.append(Candle(price - 1.5, price, price - 2.0, price - 1.0))

    return candles


def _bear_sequence():
    candles = []
    price = 200.0

    for _ in range(8):
        candles.append(Candle(price, price + 0.4, price - 0.4, price - 0.1))
        price -= 0.1

    for _ in range(22):
        price -= 1.0
        candles.append(Candle(price + 0.2, price + 0.35, price - 0.5, price - 0.25))

    candles.append(Candle(price - 0.2, price + 8.5, price - 0.3, price + 6.5))
    candles.append(Candle(price + 6.5, price + 7.0, price + 3.5, price + 4.0))
    candles.append(Candle(price + 4.0, price + 4.3, price + 1.0, price + 1.5))
    candles.append(Candle(price + 1.5, price + 2.0, price, price + 1.0))

    return candles


def test_detects_bull_twenty_gap_and_first_touch_reaction():
    result = TwentyGapBarsDynamics().analyze(_bull_sequence())

    assert result.valid is True
    assert result.direction == "UP"
    assert result.gap_bar_count >= 20
    assert result.first_touch is True
    assert result.stretched_trend is True
    assert result.state in {
        "FIRST_TOUCH_REACTION_CONFIRMED",
        "FIRST_TOUCH_OVERSHOOT_WAIT",
        "FIRST_TOUCH_WAIT",
    }


def test_detects_bear_twenty_gap_sequence():
    result = TwentyGapBarsDynamics().analyze(_bear_sequence())

    assert result.valid is True
    assert result.direction == "DOWN"
    assert result.gap_bar_count >= 20
    assert result.first_touch is True


def test_active_sequence_before_first_touch():
    candles = _bull_sequence(include_touch=False)
    result = TwentyGapBarsDynamics().analyze(candles)

    assert result.valid is True
    assert result.direction == "UP"
    assert result.first_touch is False
    assert result.state == "TWENTY_GAP_ACTIVE"


def test_current_candle_cannot_create_first_touch():
    result = TwentyGapBarsDynamics().analyze(
        _bull_sequence(include_touch=False, current_touch=True)
    )

    assert result.valid is True
    assert result.first_touch is False
    assert result.state == "TWENTY_GAP_ACTIVE"


def test_insufficient_history_is_rejected():
    candles = [Candle(100, 101, 99, 100.5) for _ in range(10)]
    result = TwentyGapBarsDynamics().analyze(candles)

    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
