from dataclasses import dataclass

from analysis.price_action.final_flag_reversal_dynamics import FinalFlagReversalDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def _uptrend_then_flag(confirm=True):
    candles = []
    p = 100.0
    for _ in range(18):
        candles.append(C(p, p + 2.0, p - 0.5, p + 1.5))
        p += 1.2

    base = p
    flag = [
        C(base, base + 1.5, base - 1.0, base + 0.5),
        C(base + .4, base + 1.2, base - .8, base - .3),
        C(base - .2, base + 1.1, base - 1.1, base + .4),
        C(base + .3, base + 1.4, base - .7, base - .2),
        C(base - .1, base + 1.0, base - 1.0, base + .3),
        C(base + .2, base + 1.3, base - .8, base - .1),
    ]
    candles.extend(flag)
    # failed upside continuation attempt
    candles.append(C(base + .2, base + 2.0, base - .7, base - .4))
    if confirm:
        candles.append(C(base - .3, base, base - 2.0, base - 1.5))
    else:
        candles.append(C(base - .3, base + .6, base - .9, base - .1))
    # current/open candle: must be ignored
    candles.append(C(base - 1.5, base + 4.0, base - 2.0, base + 3.5))
    return candles


def test_final_flag_sell_confirmed():
    r = FinalFlagReversalDynamics().analyze(_uptrend_then_flag(True), old_trend="UP")
    assert r.valid
    assert r.reversal_direction == "SELL"
    assert r.state == "FINAL_FLAG_REVERSAL_CONFIRMED"
    assert r.failed_continuation
    assert r.follow_through
    assert r.reversal_confirmed
    assert not r.old_trend_continuation_risk


def test_failed_continuation_without_follow_through_waits():
    r = FinalFlagReversalDynamics().analyze(_uptrend_then_flag(False), old_trend="UP")
    assert r.valid
    assert r.failed_continuation
    assert not r.reversal_confirmed
    assert r.state == "FINAL_FLAG_FAILED_CONTINUATION"
    assert r.old_trend_continuation_risk


def test_current_candle_does_not_confirm():
    candles = _uptrend_then_flag(False)
    # current candle is violently bearish, but analyzer excludes it
    candles[-1] = C(candles[-2].close, candles[-2].close + .2, candles[-2].close - 5, candles[-2].close - 4)
    r = FinalFlagReversalDynamics().analyze(candles, old_trend="UP")
    assert not r.reversal_confirmed


def test_insufficient_history():
    r = FinalFlagReversalDynamics().analyze([C(1, 2, 0, 1)] * 5, old_trend="UP")
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_invalid_old_trend():
    candles = _uptrend_then_flag(True)
    r = FinalFlagReversalDynamics().analyze(candles, old_trend="SIDEWAYS")
    assert not r.valid
    assert "NO_CLEAR_OLD_TREND" in r.reasons
