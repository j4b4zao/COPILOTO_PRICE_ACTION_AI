"""Linhas de tendência informativas inspiradas em Brooks Trends, capítulo 13."""

from statistics import median

from enums.trend import Trend


class TrendLineDynamics:

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
        pivots = cls._pivots(window, direction)
        if len(pivots) < 2:
            return cls._empty("INSUFFICIENT_SWINGS", direction)

        first_index, first_price = pivots[-2]
        second_index, second_price = pivots[-1]
        slope = (second_price - first_price) / (
            second_index - first_index
        )
        if not cls._valid_slope(slope, direction):
            return cls._empty("INVALID_SLOPE", direction)

        current_index = len(window) - 1
        level = first_price + slope * (current_index - first_index)
        current = window[-1]
        typical_range = cls._typical_range(window)
        tolerance = typical_range * cls.TOLERANCE_RATIO
        distance = cls._distance(current, level, direction)
        broken = cls._broken(current, level, tolerance, direction)
        tested = cls._tested(current, level, tolerance, direction)
        rejected = tested and not broken and cls._rejected(
            current,
            level,
            direction,
        )
        touch_count = cls._touch_count(
            window,
            first_index,
            first_price,
            slope,
            tolerance,
            direction,
        )
        break_strength = (
            abs(distance) / typical_range
            if broken and typical_range > 0.0
            else 0.0
        )

        return {
            "brooks_trend_line_state": cls._state(
                broken,
                tested,
                rejected,
            ),
            "brooks_trend_line_direction": direction,
            "brooks_trend_line_slope": round(slope, 4),
            "brooks_trend_line_level": round(level, 4),
            "brooks_trend_line_distance": round(distance, 4),
            "brooks_trend_line_tolerance": round(tolerance, 4),
            "brooks_trend_line_touch_count": touch_count,
            "brooks_trend_line_tested": tested,
            "brooks_trend_line_rejected": rejected,
            "brooks_trend_line_broken": broken,
            "brooks_trend_line_break_strength": round(
                break_strength,
                4,
            ),
            "brooks_trend_line_two_sided_risk": broken,
            "brooks_trend_line_valid": True,
        }

    @staticmethod
    def _direction(trend):
        if trend == Trend.UP:
            return "UP"
        if trend == Trend.DOWN:
            return "DOWN"
        return "NONE"

    @staticmethod
    def _pivots(candles, direction):
        pivots = []
        for index in range(1, len(candles) - 1):
            previous = candles[index - 1]
            current = candles[index]
            following = candles[index + 1]
            if direction == "UP":
                pivot = (
                    current.low <= previous.low
                    and current.low <= following.low
                )
                price = current.low
            else:
                pivot = (
                    current.high >= previous.high
                    and current.high >= following.high
                )
                price = current.high
            if pivot:
                pivots.append((index, price))
        return pivots

    @staticmethod
    def _valid_slope(slope, direction):
        return slope >= 0.0 if direction == "UP" else slope <= 0.0

    @staticmethod
    def _typical_range(candles):
        ranges = [candle.range for candle in candles if candle.range > 0.0]
        return median(ranges) if ranges else 0.0

    @staticmethod
    def _distance(candle, level, direction):
        if direction == "UP":
            return candle.low - level
        return level - candle.high

    @staticmethod
    def _broken(candle, level, tolerance, direction):
        if direction == "UP":
            return candle.close < level - tolerance
        return candle.close > level + tolerance

    @staticmethod
    def _tested(candle, level, tolerance, direction):
        if direction == "UP":
            return candle.low <= level + tolerance
        return candle.high >= level - tolerance

    @staticmethod
    def _rejected(candle, level, direction):
        if direction == "UP":
            return candle.close > level and candle.bullish
        return candle.close < level and candle.bearish

    @classmethod
    def _touch_count(
        cls,
        candles,
        anchor_index,
        anchor_price,
        slope,
        tolerance,
        direction,
    ):
        count = 0
        for index in range(anchor_index, len(candles)):
            level = anchor_price + slope * (index - anchor_index)
            price = (
                candles[index].low
                if direction == "UP"
                else candles[index].high
            )
            if abs(price - level) <= tolerance:
                count += 1
        return count

    @staticmethod
    def _state(broken, tested, rejected):
        if broken:
            return "LINE_BREAK"
        if rejected:
            return "LINE_REJECTION"
        if tested:
            return "LINE_TEST"
        return "LINE_HOLD"

    @staticmethod
    def _empty(state, direction="NONE"):
        return {
            "brooks_trend_line_state": state,
            "brooks_trend_line_direction": direction,
            "brooks_trend_line_slope": 0.0,
            "brooks_trend_line_level": 0.0,
            "brooks_trend_line_distance": 0.0,
            "brooks_trend_line_tolerance": 0.0,
            "brooks_trend_line_touch_count": 0,
            "brooks_trend_line_tested": False,
            "brooks_trend_line_rejected": False,
            "brooks_trend_line_broken": False,
            "brooks_trend_line_break_strength": 0.0,
            "brooks_trend_line_two_sided_risk": False,
            "brooks_trend_line_valid": False,
        }
