from dataclasses import dataclass

from analysis.price_action.trade_trap_dynamics import TradeTrapDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def _base():
    return [
        C(100, 102, 99, 101),
        C(101, 103, 100, 102),
        C(102, 104, 101, 103),
        C(103, 105, 102, 104),
        C(104, 106, 103, 105),
    ]


def test_trap_in_when_entering_before_weak_signal_close():
    candles = _base() + [
        C(105, 107, 104, 104.2),  # signal deteriorates by close
        C(104.2, 105, 103.5, 104.0),
        C(104, 106, 103.8, 105.5),  # current/forming, excluded
    ]

    r = TradeTrapDynamics().analyze(
        candles,
        "BUY",
        signal_index=5,
        entry_index=6,
        entered_before_signal_close=True,
    )

    assert r.valid
    assert r.trap_in
    assert r.state == "TRAPPED_IN"
    assert r.signal_deteriorated


def test_trap_out_when_stop_tightened_and_original_plan_still_valid():
    candles = _base() + [
        C(105, 106, 104, 105.6),
        C(105.6, 107, 105.2, 106.7),
        C(106.7, 108, 106.5, 107.8),
        C(107.8, 109, 107.5, 108.8),  # current excluded
    ]

    r = TradeTrapDynamics().analyze(
        candles,
        "BUY",
        signal_index=5,
        entry_index=6,
        original_stop=103.5,
        tightened_stop=105.0,
        stopped_out=True,
        original_plan_valid=True,
    )

    assert r.valid
    assert r.trap_out
    assert r.reentry_watch
    assert r.state == "TRAPPED_OUT"


def test_strong_entry_close_supports_holding_remainder():
    candles = _base() + [
        C(105, 106, 104.5, 105.5),
        C(105.5, 108, 105.4, 107.7),
        C(107.7, 110, 107.5, 109.7),
        C(109.7, 111, 109.5, 110.8),  # current excluded
    ]

    r = TradeTrapDynamics().analyze(
        candles,
        "BUY",
        signal_index=5,
        entry_index=6,
        original_plan_valid=True,
    )

    assert r.valid
    assert r.entry_bar_strong_close
    assert r.breakeven_hold_preferred
    assert r.state == "PLAN_HOLD_SUPPORTED"


def test_current_candle_cannot_create_follow_through():
    candles = _base() + [
        C(105, 106, 104.5, 105.4),
        C(105.4, 106, 104.9, 105.5),
        C(105.5, 110, 105.4, 109.8),  # current/forming only
    ]

    r = TradeTrapDynamics().analyze(
        candles,
        "BUY",
        signal_index=5,
        entry_index=6,
    )

    assert r.valid
    assert not r.follow_through_strong


def test_invalid_direction():
    r = TradeTrapDynamics().analyze(_base() + [C(105, 106, 104, 105)], "NONE")
    assert not r.valid
    assert r.reason == "INVALID_DIRECTION"


def test_insufficient_history():
    r = TradeTrapDynamics().analyze([C(1, 2, 0, 1), C(1, 2, 0, 1)], "BUY")
    assert not r.valid
    assert r.reason == "INSUFFICIENT_HISTORY"
