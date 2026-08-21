from types import SimpleNamespace

from analysis.price_action.bar_count_dynamics import BarCountDynamics


def c(open_, high, low, close):
    return SimpleNamespace(open=open_, high=high, low=low, close=close)


def bull_h2_sequence():
    closed = [
        c(100, 101, 99.5, 100.8),
        c(100.8, 102, 100.5, 101.8),
        c(101.8, 103, 101.5, 102.8),
        c(102.8, 104, 102.5, 103.8),
        c(103.8, 105, 103.5, 104.8),
        c(104.8, 107, 104.5, 106.8),
        c(106.8, 109, 106.5, 108.8),
        c(108.8, 111, 108.5, 110.5),
        c(110.5, 110.7, 107.0, 107.5),   # first counter leg
        c(107.5, 109.5, 106.8, 108.8),   # H1
        c(108.8, 109.0, 104.0, 105.0),   # H1 failure / second leg
        c(105.0, 106.0, 103.0, 104.0),
        c(104.0, 107.0, 103.5, 106.5),   # H2
        c(106.5, 108.5, 106.2, 108.0),   # confirmation
    ]
    return closed + [c(108.0, 109.0, 107.5, 108.5)]  # current/forming


def bear_l2_sequence():
    closed = [
        c(120, 120.5, 119, 119.2),
        c(119.2, 119.5, 118, 118.2),
        c(118.2, 118.5, 117, 117.2),
        c(117.2, 117.5, 116, 116.2),
        c(116.2, 116.5, 115, 115.2),
        c(115.2, 115.5, 113, 113.2),
        c(113.2, 113.5, 111, 111.2),
        c(111.2, 111.5, 109, 109.5),
        c(109.5, 113.0, 109.3, 112.5),   # first counter leg
        c(112.5, 113.2, 110.5, 111.0),   # L1
        c(111.0, 115.0, 110.8, 114.0),   # L1 failure / second leg
        c(114.0, 116.0, 113.0, 115.0),
        c(115.0, 115.5, 112.0, 112.5),   # L2
        c(112.5, 112.8, 110.0, 110.5),   # confirmation
    ]
    return closed + [c(110.5, 111.0, 109.5, 110.0)]


def test_high2_abc_buy_setup_is_detected():
    result = BarCountDynamics().analyze(bull_h2_sequence())
    assert result.valid is True
    assert result.trend_direction == "UP"
    assert result.pattern == "HIGH_2"
    assert result.setup_direction == "BUY"
    assert result.first_attempt_failed is True
    assert result.two_leg_pullback is True
    assert result.abc_correction is True
    assert result.signal_confirmed is True
    assert result.continuation_bias is True


def test_low2_abc_sell_setup_is_detected():
    result = BarCountDynamics().analyze(bear_l2_sequence())
    assert result.valid is True
    assert result.trend_direction == "DOWN"
    assert result.pattern == "LOW_2"
    assert result.setup_direction == "SELL"
    assert result.two_leg_pullback is True
    assert result.abc_correction is True
    assert result.signal_confirmed is True
    assert result.continuation_bias is True


def test_current_candle_cannot_create_high2_confirmation():
    candles = bull_h2_sequence()
    # Remove the closed H2 and confirmation, then make the forming candle look
    # like an H2. Since the last candle is excluded, H2 must not be confirmed.
    truncated = candles[:12] + [c(104.0, 107.0, 103.5, 106.5)]
    result = BarCountDynamics().analyze(truncated)
    assert result.pattern != "HIGH_2" or result.signal_confirmed is False


def test_insufficient_history_is_rejected():
    candles = [c(100, 101, 99, 100.5) for _ in range(8)]
    result = BarCountDynamics().analyze(candles)
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
