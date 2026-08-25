"""Entradas tardias informativas inspiradas em Brooks Trends, capítulo 11."""

from statistics import median

from enums.trend import Trend


class LateEntryDynamics:

    LOOKBACK = 12
    MIN_TREND_BARS = 4
    CLIMAX_BARS = 8
    CLIMAX_RANGE_RATIO = 1.80
    MIN_EFFICIENCY = 0.65

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])
        if len(closed) < 5:
            return {}

        direction = cls._direction(trend)
        if direction == "NONE":
            return cls._empty_metrics()

        window = closed[-cls.LOOKBACK:]
        streak = cls._trailing_streak(window, direction)
        pullback_available = False
        leg = window[-streak:] if streak else []

        if streak == 0 and cls._is_counter_bar(window[-1], direction):
            prior_streak = cls._trailing_streak(window[:-1], direction)
            if prior_streak >= cls.MIN_TREND_BARS:
                pullback_available = True
                streak = prior_streak
                leg = window[-(prior_streak + 1):-1]

        efficiency = cls._efficiency(leg)
        range_ratio = cls._range_ratio(window, leg)
        climax_risk = (
            streak >= cls.CLIMAX_BARS
            or range_ratio >= cls.CLIMAX_RANGE_RATIO
        )
        missed_entry = streak >= cls.MIN_TREND_BARS
        late_candidate = missed_entry and not climax_risk
        stop_reference = cls._stop_reference(leg, direction)
        stop_distance = cls._stop_distance(
            window[-1].close,
            stop_reference,
        )
        state = cls._state(
            missed_entry,
            late_candidate,
            pullback_available,
            climax_risk,
        )

        return {
            "brooks_late_entry_state": state,
            "brooks_late_entry_direction": direction,
            "brooks_late_entry_trend_bars": streak,
            "brooks_late_entry_efficiency": round(efficiency, 4),
            "brooks_late_entry_range_ratio": round(range_ratio, 4),
            "brooks_late_entry_stop_reference": round(stop_reference, 4),
            "brooks_late_entry_stop_distance": round(stop_distance, 4),
            "brooks_late_entry_missed": missed_entry,
            "brooks_late_entry_candidate": late_candidate,
            "brooks_late_entry_pullback_available": pullback_available,
            "brooks_late_entry_climax_risk": climax_risk,
            "brooks_late_entry_reduce_position": late_candidate,
            "brooks_late_entry_confirmed": (
                late_candidate
                and efficiency >= cls.MIN_EFFICIENCY
            ),
        }

    @classmethod
    def _empty_metrics(cls):
        return {
            "brooks_late_entry_state": "NO_CLEAR_TREND",
            "brooks_late_entry_direction": "NONE",
            "brooks_late_entry_trend_bars": 0,
            "brooks_late_entry_efficiency": 0.0,
            "brooks_late_entry_range_ratio": 0.0,
            "brooks_late_entry_stop_reference": 0.0,
            "brooks_late_entry_stop_distance": 0.0,
            "brooks_late_entry_missed": False,
            "brooks_late_entry_candidate": False,
            "brooks_late_entry_pullback_available": False,
            "brooks_late_entry_climax_risk": False,
            "brooks_late_entry_reduce_position": False,
            "brooks_late_entry_confirmed": False,
        }

    @staticmethod
    def _direction(trend):
        if trend == Trend.UP:
            return "BUY"
        if trend == Trend.DOWN:
            return "SELL"
        return "NONE"

    @classmethod
    def _trailing_streak(cls, candles, direction):
        count = 0
        for candle in reversed(candles):
            if not cls._is_trend_bar(candle, direction):
                break
            count += 1
        return count

    @staticmethod
    def _is_trend_bar(candle, direction):
        if direction == "BUY":
            return candle.bullish
        return candle.bearish

    @staticmethod
    def _is_counter_bar(candle, direction):
        if direction == "BUY":
            return candle.bearish
        return candle.bullish

    @staticmethod
    def _efficiency(leg):
        if len(leg) < 2:
            return 0.0
        closes = [candle.close for candle in leg]
        travel = sum(
            abs(current - previous)
            for previous, current in zip(closes, closes[1:])
        )
        if travel <= 0.0:
            return 0.0
        return abs(closes[-1] - closes[0]) / travel

    @classmethod
    def _range_ratio(cls, window, leg):
        if not leg:
            return 0.0
        reference = window[:-len(leg)]
        ranges = [candle.range for candle in reference if candle.range > 0.0]
        typical = median(ranges) if ranges else 0.0
        if typical <= 0.0:
            return 0.0
        return max(candle.range for candle in leg) / typical

    @staticmethod
    def _stop_reference(leg, direction):
        if not leg:
            return 0.0
        if direction == "BUY":
            return min(candle.low for candle in leg)
        return max(candle.high for candle in leg)

    @staticmethod
    def _stop_distance(close, stop_reference):
        if stop_reference == 0.0:
            return 0.0
        return abs(close - stop_reference)

    @staticmethod
    def _state(missed, candidate, pullback, climax):
        if not missed:
            return "NO_LATE_ENTRY"
        if climax:
            return "AVOID_CHASING"
        if pullback:
            return "PULLBACK_AVAILABLE"
        if candidate:
            return "LATE_ENTRY_CANDIDATE"
        return "WAIT"
