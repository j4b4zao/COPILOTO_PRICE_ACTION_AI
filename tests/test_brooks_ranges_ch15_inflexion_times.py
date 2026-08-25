from datetime import datetime, timedelta, time

from analysis.price_action.inflexion_time_dynamics import InflexionTimeDynamics


class Candle:
    def __init__(self, timestamp, open_, high, low, close):
        self.timestamp = timestamp
        self.open = open_
        self.high = high
        self.low = low
        self.close = close


def bar(ts, o, h, l, c):
    return Candle(ts, o, h, l, c)


def build_session(start, count=12, step=5, base=100.0):
    candles = []
    price = base
    for i in range(count):
        ts = start + timedelta(minutes=i * step)
        candles.append(bar(ts, price, price + 1.0, price - 1.0, price + 0.2))
        price += 0.2
    return candles


def test_opening_hour_breakout_is_temporal_context():
    start = datetime(2026, 8, 21, 9, 0)
    candles = build_session(start, count=11, step=5)
    ts = start + timedelta(minutes=55)
    candles.append(bar(ts, 102.0, 106.0, 101.8, 105.8))  # closed breakout
    candles.append(bar(ts + timedelta(minutes=5), 105.8, 106.2, 105.5, 106.0))  # forming

    result = InflexionTimeDynamics().analyze(candles, session_start=time(9, 0))

    assert result.valid is True
    assert result.phase == "OPENING_HOUR"
    assert result.in_inflexion_window is True
    assert result.breakout_detected is True
    assert result.breakout_direction == "UP"
    assert result.temporal_context_only is True


def test_midday_bear_reversal_is_detected():
    start = datetime(2026, 8, 21, 9, 0)
    candles = build_session(start, count=34, step=5, base=100.0)
    ts = start + timedelta(minutes=170)
    # New high and strong bearish close near the low.
    candles[-1] = bar(ts, 108.0, 111.0, 106.0, 106.5)
    candles.append(bar(ts + timedelta(minutes=5), 106.5, 107.0, 106.0, 106.8))

    result = InflexionTimeDynamics().analyze(candles, session_start=time(9, 0))

    assert result.valid is True
    assert result.phase == "MIDDAY_INFLEXION"
    assert result.reversal_detected is True
    assert result.reversal_direction == "DOWN"


def test_late_session_window_uses_configured_close():
    start = datetime(2026, 8, 21, 9, 0)
    candles = build_session(start, count=73, step=5)
    last_closed = start + timedelta(minutes=360)
    candles[-1].timestamp = last_closed
    candles.append(bar(last_closed + timedelta(minutes=5), 114, 115, 113, 114.5))

    result = InflexionTimeDynamics().analyze(
        candles,
        session_start=time(9, 0),
        session_end=time(16, 0),
    )

    assert result.phase == "LATE_SESSION_INFLEXION"
    assert result.minutes_to_close == 60
    assert result.in_inflexion_window is True


def test_current_forming_candle_cannot_create_breakout():
    start = datetime(2026, 8, 21, 9, 0)
    candles = build_session(start, count=12, step=5)
    forming_ts = start + timedelta(minutes=60)
    candles.append(bar(forming_ts, 102.0, 110.0, 101.0, 109.5))

    result = InflexionTimeDynamics().analyze(candles, session_start=time(9, 0))

    assert result.breakout_detected is False


def test_insufficient_history():
    start = datetime(2026, 8, 21, 9, 0)
    candles = build_session(start, count=6, step=5)

    result = InflexionTimeDynamics().analyze(candles, session_start=time(9, 0))

    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
