from dataclasses import dataclass

from analysis.price_action.trade_style_dynamics import TradeStyleDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_tight_range_becomes_no_trade():
    candles = []
    price = 100.0
    for i in range(14):
        o = price + (0.05 if i % 2 == 0 else -0.05)
        c = price + (-0.04 if i % 2 == 0 else 0.04)
        candles.append(C(o, 100.35, 99.65, c))
    candles.append(C(100.0, 100.2, 99.8, 100.0))  # current

    result = TradeStyleDynamics().analyze(candles)

    assert result.valid is True
    assert result.style == "NO_TRADE"
    assert result.no_trade is True
    assert result.investing_applicable is False


def test_strong_trend_with_room_prefers_swing():
    candles = []
    price = 100.0
    for _ in range(14):
        candles.append(C(price, price + 1.1, price - 0.2, price + 0.9))
        price += 0.85
    candles.append(C(price, price + 3.0, price - 3.0, price))  # current

    last_closed = candles[-2].close
    result = TradeStyleDynamics().analyze(
        candles,
        structural_target=last_closed + 4.0,
        stop_price=last_closed - 2.0,
    )

    assert result.valid is True
    assert result.context == "TREND"
    assert result.style == "SWING"
    assert result.swing_appropriate is True
    assert result.scalp_appropriate is False


def test_range_without_large_space_prefers_scalp():
    candles = [
        C(100.0, 101.0, 99.0, 100.6),
        C(100.6, 101.4, 99.8, 100.1),
        C(100.1, 101.2, 99.5, 100.7),
        C(100.7, 101.6, 99.7, 100.0),
    ] * 4
    candles.append(C(100.0, 102.0, 98.0, 100.0))  # current

    result = TradeStyleDynamics().analyze(candles)

    assert result.valid is True
    assert result.context in ("TRADING_RANGE", "TIGHT_TRADING_RANGE")
    if result.context == "TRADING_RANGE":
        assert result.style == "SCALP"
        assert result.scalp_appropriate is True


def test_current_candle_does_not_change_management_style():
    base = []
    price = 100.0
    for _ in range(14):
        base.append(C(price, price + 1.0, price - 0.2, price + 0.8))
        price += 0.75

    a = base + [C(price, price + 1.0, price - 1.0, price)]
    b = base + [C(price, price + 50.0, price - 50.0, price - 40.0)]

    ra = TradeStyleDynamics().analyze(a)
    rb = TradeStyleDynamics().analyze(b)

    assert ra.to_dict() == rb.to_dict()


def test_insufficient_history():
    candles = [C(100.0, 101.0, 99.0, 100.5)] * 8
    result = TradeStyleDynamics().analyze(candles)

    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
