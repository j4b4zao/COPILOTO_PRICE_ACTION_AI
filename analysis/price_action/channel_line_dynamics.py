"""Linhas de canal informativas inspiradas em Brooks Trends, capítulo 14."""

from analysis.price_action.trend_line_dynamics import TrendLineDynamics
from enums.trend import Trend


class ChannelLineDynamics:

    LOOKBACK = 20
    TOLERANCE_RATIO = 0.15

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])
        if len(closed) < 7:
            return {}

        direction = cls._direction(trend)
        if direction == "NONE":
            return cls._empty("NO_CLEAR_TREND")

        window = closed[-cls.LOOKBACK:]
        pivots = TrendLineDynamics._pivots(window, direction)
        if len(pivots) < 2:
            return cls._empty("INSUFFICIENT_SWINGS", direction)

        first_index, first_price = pivots[-2]
        second_index, second_price = pivots[-1]
        slope = (second_price - first_price) / (
            second_index - first_index
        )
        if not TrendLineDynamics._valid_slope(slope, direction):
            return cls._empty("INVALID_SLOPE", direction)

        width = cls._channel_width(
            window,
            first_index,
            second_index,
            first_price,
            slope,
            direction,
        )
        if width <= 0.0:
            return cls._empty("INVALID_WIDTH", direction)

        current_index = len(window) - 1
        base_level = first_price + slope * (
            current_index - first_index
        )
        channel_level = cls._channel_level(
            base_level,
            width,
            direction,
        )
        lower, upper = cls._bounds(
            base_level,
            channel_level,
        )
        current = window[-1]
        typical_range = TrendLineDynamics._typical_range(window)
        tolerance = typical_range * cls.TOLERANCE_RATIO
        tested = cls._tested(
            current,
            channel_level,
            tolerance,
            direction,
        )
        overshoot = cls._overshoot(
            current,
            channel_level,
            tolerance,
            direction,
        )
        returned_inside = overshoot and cls._returned_inside(
            current,
            channel_level,
            direction,
        )
        accelerating = overshoot and not returned_inside
        overshoot_distance = cls._overshoot_distance(
            current,
            channel_level,
            direction,
        ) if overshoot else 0.0
        position = (current.close - lower) / width

        return {
            "brooks_channel_line_state": cls._state(
                tested,
                overshoot,
                returned_inside,
                accelerating,
            ),
            "brooks_channel_line_direction": direction,
            "brooks_channel_line_slope": round(slope, 4),
            "brooks_channel_line_trend_level": round(base_level, 4),
            "brooks_channel_line_level": round(channel_level, 4),
            "brooks_channel_line_width": round(width, 4),
            "brooks_channel_line_position": round(position, 4),
            "brooks_channel_line_tolerance": round(tolerance, 4),
            "brooks_channel_line_overshoot_distance": round(
                overshoot_distance,
                4,
            ),
            "brooks_channel_line_tested": tested,
            "brooks_channel_line_overshoot": overshoot,
            "brooks_channel_line_returned_inside": returned_inside,
            "brooks_channel_line_accelerating": accelerating,
            "brooks_channel_line_reversal_candidate": returned_inside,
            "brooks_channel_line_valid": True,
        }

    @staticmethod
    def _direction(trend):
        if trend == Trend.UP:
            return "UP"
        if trend == Trend.DOWN:
            return "DOWN"
        return "NONE"

    @staticmethod
    def _channel_width(
        candles,
        first_index,
        second_index,
        first_price,
        slope,
        direction,
    ):
        distances = []
        for index in range(first_index, second_index + 1):
            base = first_price + slope * (index - first_index)
            distance = (
                candles[index].high - base
                if direction == "UP"
                else base - candles[index].low
            )
            distances.append(distance)
        return max(distances, default=0.0)

    @staticmethod
    def _channel_level(base_level, width, direction):
        if direction == "UP":
            return base_level + width
        return base_level - width

    @staticmethod
    def _bounds(base_level, channel_level):
        return min(base_level, channel_level), max(base_level, channel_level)

    @staticmethod
    def _tested(candle, level, tolerance, direction):
        if direction == "UP":
            return candle.high >= level - tolerance
        return candle.low <= level + tolerance

    @staticmethod
    def _overshoot(candle, level, tolerance, direction):
        if direction == "UP":
            return candle.high > level + tolerance
        return candle.low < level - tolerance

    @staticmethod
    def _returned_inside(candle, level, direction):
        if direction == "UP":
            return candle.close < level
        return candle.close > level

    @staticmethod
    def _overshoot_distance(candle, level, direction):
        if direction == "UP":
            return max(0.0, candle.high - level)
        return max(0.0, level - candle.low)

    @staticmethod
    def _state(tested, overshoot, returned_inside, accelerating):
        if returned_inside:
            return "OVERSHOOT_REVERSAL"
        if accelerating:
            return "CHANNEL_BREAKOUT"
        if overshoot:
            return "CHANNEL_OVERSHOOT"
        if tested:
            return "CHANNEL_LINE_TEST"
        return "CHANNEL_CONTAINED"

    @staticmethod
    def _empty(state, direction="NONE"):
        return {
            "brooks_channel_line_state": state,
            "brooks_channel_line_direction": direction,
            "brooks_channel_line_slope": 0.0,
            "brooks_channel_line_trend_level": 0.0,
            "brooks_channel_line_level": 0.0,
            "brooks_channel_line_width": 0.0,
            "brooks_channel_line_position": 0.5,
            "brooks_channel_line_tolerance": 0.0,
            "brooks_channel_line_overshoot_distance": 0.0,
            "brooks_channel_line_tested": False,
            "brooks_channel_line_overshoot": False,
            "brooks_channel_line_returned_inside": False,
            "brooks_channel_line_accelerating": False,
            "brooks_channel_line_reversal_candidate": False,
            "brooks_channel_line_valid": False,
        }
