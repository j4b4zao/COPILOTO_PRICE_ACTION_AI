from dataclasses import dataclass

from analysis.price_action.huge_volume_reversal_dynamics import HugeVolumeReversalDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float
    volume: float


def test_insufficient_history():
    candles = [C(10, 11, 9, 10.5, 100) for _ in range(8)]
    result = HugeVolumeReversalDynamics().analyze(candles, "D1")
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_huge_volume_alone_does_not_confirm_reversal():
    candles = []
    price = 100.0
    for _ in range(12):
        candles.append(C(price, price + 2, price - 0.5, price + 1.5, 100))
        price += 1.5
    candles.append(C(price, price + 4, price - 1, price + 3, 350))
    candles.append(C(price + 3, price + 5, price + 2, price + 4, 110))
    candles.append(C(price + 4, price + 5, price + 3, price + 4.2, 100))
    candles.append(C(price + 4.2, price + 4.5, price + 3.8, price + 4.0, 90))  # current

    result = HugeVolumeReversalDynamics().analyze(candles, "D1")
    assert result.huge_volume is True
    assert result.reversal_confirmed is False
    assert result.continuation_risk is True


def test_daily_sell_reversal_after_huge_volume_climax():
    candles = []
    price = 100.0
    for _ in range(12):
        candles.append(C(price, price + 2.2, price - 0.4, price + 1.6, 100))
        price += 1.6

    candles.append(C(price, price + 6, price - 0.5, price + 1.0, 360))
    candles.append(C(price + 1.0, price + 1.5, price - 2.0, price - 1.5, 150))
    candles.append(C(price - 1.5, price - 1.0, price - 4.0, price - 3.0, 140))
    candles.append(C(price - 3.0, price - 2.0, price - 4.0, price - 2.5, 120))  # current

    result = HugeVolumeReversalDynamics().analyze(candles, "D1")
    assert result.canonical_daily_context is True
    assert result.old_trend == "UP"
    assert result.reversal_direction == "SELL"
    assert result.reversal_confirmed is True
    assert result.pattern == "HUGE_VOLUME_REVERSAL_CONFIRMED"


def test_current_candle_is_excluded():
    base = [C(100 + i, 102 + i, 99 + i, 101.5 + i, 100) for i in range(15)]
    current = C(115, 125, 110, 111, 1000)
    result = HugeVolumeReversalDynamics().analyze(base + [current], "D1")
    assert result.huge_volume is False


def test_intraday_is_allowed_but_not_canonical_daily_context():
    candles = [C(100 + i, 102 + i, 99 + i, 101 + i, 100) for i in range(15)]
    result = HugeVolumeReversalDynamics().analyze(candles + [candles[-1]], "M5")
    assert result.canonical_daily_context is False
