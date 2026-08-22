from dataclasses import dataclass

from analysis.price_action.stop_entry_dynamics import StopEntryDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def test_buy_stop_entry_triggers_above_signal_high_and_tightens_on_strong_entry():
    candles = [
        Candle(100, 102, 99, 101),
        Candle(101, 103, 100, 102),
        Candle(102, 104, 101, 103),
        Candle(103, 105, 102, 104),  # signal
        Candle(104, 108, 103, 107.5),  # strong entry bar
        Candle(107.5, 109, 107, 108),  # current/forming -> excluded
    ]

    result = StopEntryDynamics().analyze(
        candles,
        direction="BUY",
        tick_size=1.0,
        signal_index=3,
    )

    assert result.valid is True
    assert result.trigger_price == 106.0
    assert result.initial_protective_stop == 101.0
    assert result.trigger_hit is True
    assert result.strong_entry_bar is True
    assert result.tighten_stop_allowed is True
    assert result.tightened_stop == 102.0


def test_sell_stop_entry_triggers_below_signal_low():
    candles = [
        Candle(110, 111, 108, 109),
        Candle(109, 110, 106, 107),
        Candle(107, 108, 104, 105),
        Candle(105, 106, 102, 103),  # signal
        Candle(103, 104, 98, 99),  # entry
        Candle(99, 101, 97, 100),  # current/forming -> excluded
    ]

    result = StopEntryDynamics().analyze(
        candles,
        direction="SELL",
        tick_size=1.0,
        signal_index=3,
    )

    assert result.valid is True
    assert result.trigger_price == 101.0
    assert result.initial_protective_stop == 107.0
    assert result.trigger_hit is True
    assert result.entry_index == 4


def test_pending_when_closed_bars_do_not_reach_trigger():
    candles = [
        Candle(100, 102, 99, 101),
        Candle(101, 103, 100, 102),
        Candle(102, 104, 101, 103),
        Candle(103, 105, 102, 104),  # signal -> BUY trigger 106
        Candle(104, 105.5, 103, 105),  # no trigger
        Candle(105, 107, 104, 106.5),  # current only would trigger
    ]

    result = StopEntryDynamics().analyze(
        candles,
        direction="BUY",
        tick_size=1.0,
        signal_index=3,
    )

    assert result.state == "STOP_ENTRY_PENDING"
    assert result.trigger_hit is False
    assert result.current_candle_excluded is True


def test_weak_entry_bar_keeps_stop_beyond_signal_bar():
    candles = [
        Candle(100, 102, 99, 101),
        Candle(101, 103, 100, 102),
        Candle(102, 104, 101, 103),
        Candle(103, 105, 102, 104),  # signal
        Candle(104, 106.5, 102.5, 104.5),  # trigger, weak close/body
        Candle(104.5, 107, 104, 106),
    ]

    result = StopEntryDynamics().analyze(
        candles,
        direction="BUY",
        tick_size=1.0,
        signal_index=3,
    )

    assert result.trigger_hit is True
    assert result.strong_entry_bar is False
    assert result.tighten_stop_allowed is False
    assert result.tightened_stop == result.initial_protective_stop


def test_invalid_direction_and_insufficient_history():
    engine = StopEntryDynamics()

    bad_direction = engine.analyze([], direction="WAIT")
    assert bad_direction.valid is False
    assert bad_direction.reason == "INVALID_DIRECTION"

    short_history = engine.analyze(
        [Candle(100, 101, 99, 100), Candle(100, 102, 99, 101)],
        direction="BUY",
    )
    assert short_history.valid is False
    assert short_history.reason == "INSUFFICIENT_HISTORY"
