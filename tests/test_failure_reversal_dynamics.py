from types import SimpleNamespace
from analysis.price_action.failure_reversal_dynamics import FailureReversalDynamics

def c(o,h,l,cl): return SimpleNamespace(open=o, high=h, low=l, close=cl)

def base():
    return [c(100,102,99,101), c(101,103,100,102), c(102,104,101,103), c(103,105,102,104), c(104,106,103,105)]

def test_invalid_direction():
    r = FailureReversalDynamics().analyze(base()+[c(1,1,1,1)]*4, "NONE")
    assert not r.valid
    assert "INVALID_SETUP_DIRECTION" in r.reasons

def test_insufficient_history():
    r = FailureReversalDynamics().analyze([c(1,2,0,1)]*5, "BUY")
    assert not r.valid
    assert "INSUFFICIENT_HISTORY" in r.reasons

def test_failed_buy_can_confirm_sell_reversal():
    bars = base() + [
        c(105,106,104,105),   # signal
        c(105,106.2,104.8,105.4), # buy triggered, target not hit
        c(105.2,105.4,102.5,102.8), # failure + strong sell
        c(102.8,103.0,101.5,101.8), # sell follow-through
        c(200,220,190,215),   # current candle ignored
    ]
    r = FailureReversalDynamics().analyze(bars, "BUY", objective_price=108)
    assert r.failed_setup
    assert r.opposite_direction == "SELL"
    assert r.failure_reversal_confirmed
    assert r.state == "FAILURE_REVERSAL_CONFIRMED"

def test_failure_aligned_with_dominant_trend_is_second_signal():
    bars = base() + [
        c(105,106,104,105), c(105,106.2,104.8,105.4),
        c(105.2,105.4,102.5,102.8), c(102.8,103.0,101.5,101.8), c(200,220,190,215)
    ]
    r = FailureReversalDynamics().analyze(bars, "BUY", objective_price=108, dominant_trend="DOWN")
    assert r.second_signal_with_trend
    assert r.state == "SECOND_SIGNAL_WITH_TREND"

def test_successful_setup_is_not_failure():
    bars = base() + [
        c(105,106,104,105), c(105,108.5,104.8,108), c(108,109,107,108.5), c(108.5,110,108,109.5), c(1,1,1,1)
    ]
    r = FailureReversalDynamics().analyze(bars, "BUY", objective_price=108)
    assert r.objective_reached
    assert not r.failed_setup
    assert r.state == "SETUP_SUCCEEDED"

def test_current_candle_cannot_create_failure():
    bars = base() + [
        c(105,106,104,105), c(105,106.2,104.8,105.4), c(105.4,106,104.5,105.8), c(105.8,106.2,105,105.9),
        c(105.9,106,100,100.5),
    ]
    r = FailureReversalDynamics().analyze(bars, "BUY", objective_price=108)
    assert not r.failed_setup
