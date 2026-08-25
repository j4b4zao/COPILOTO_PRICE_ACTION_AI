from dataclasses import dataclass

from analysis.price_action.limit_entry_dynamics import LimitEntryDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def _range_history():
    data = []
    for i in range(16):
        base = 100.0 + (i % 4) * 0.4
        o = base + (0.2 if i % 2 == 0 else -0.1)
        c = base + (-0.1 if i % 2 == 0 else 0.2)
        data.append(C(o, 102.0, 98.0, c))
    data.append(C(100.0, 103.0, 97.0, 100.0))  # current/forming
    return data


def _strong_uptrend():
    data = []
    px = 100.0
    for _ in range(16):
        data.append(C(px, px + 1.2, px - 0.2, px + 1.0))
        px += 1.0
    data.append(C(px, px + 5.0, px - 5.0, px))  # current/forming
    return data


def test_buy_limit_near_low_is_candidate_or_touched():
    result = LimitEntryDynamics().analyze(
        _range_history(),
        "BUY",
        limit_price=98.8,
        stop_price=97.5,
        target_price=101.8,
    )
    assert result.valid is True
    assert result.favorable_location is True
    assert result.state in ("LIMIT_ENTRY_CANDIDATE", "LIMIT_ENTRY_TOUCHED")


def test_sell_limit_near_high_is_candidate_or_touched():
    result = LimitEntryDynamics().analyze(
        _range_history(),
        "SELL",
        limit_price=101.2,
        stop_price=102.5,
        target_price=98.2,
    )
    assert result.valid is True
    assert result.favorable_location is True


def test_middle_of_range_is_poor_location():
    result = LimitEntryDynamics().analyze(
        _range_history(),
        "BUY",
        limit_price=100.0,
        stop_price=97.5,
        target_price=102.0,
    )
    assert result.valid is False
    assert result.state == "LIMIT_ENTRY_POOR_LOCATION"


def test_countertrend_limit_in_strong_trend_is_blocked():
    result = LimitEntryDynamics().analyze(
        _strong_uptrend(),
        "SELL",
        limit_price=113.0,
        stop_price=116.0,
        target_price=108.0,
    )
    assert result.valid is False
    assert result.countertrend_entry is True
    assert result.strong_trend_block is True
    assert result.state == "LIMIT_ENTRY_COUNTERTREND_BLOCKED"


def test_current_candle_does_not_change_context_or_trigger_touch():
    candles = _range_history()
    result = LimitEntryDynamics().analyze(
        candles,
        "BUY",
        limit_price=97.2,  # only current candle reaches below 98
        stop_price=96.0,
        target_price=101.0,
    )
    assert result.touched is False


def test_invalid_direction():
    result = LimitEntryDynamics().analyze(_range_history(), "NONE")
    assert result.valid is False
    assert result.reason == "INVALID_DIRECTION"


def test_insufficient_history():
    short = [C(100, 101, 99, 100.5) for _ in range(8)]
    result = LimitEntryDynamics().analyze(short, "BUY")
    assert result.valid is False
    assert result.reason == "INSUFFICIENT_HISTORY"
