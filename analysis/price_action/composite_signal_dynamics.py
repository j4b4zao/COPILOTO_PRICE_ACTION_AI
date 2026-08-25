"""Padrões compostos informativos inspirados em Brooks Trends, capítulo 6."""

from statistics import median

from enums.trend import Trend


class CompositeSignalDynamics:

    DOJI_BODY_RATIO = 0.10
    TREND_BODY_RATIO = 0.30
    SMALL_RANGE_RATIO = 0.75
    SIMILAR_RANGE_RATIO = 0.60
    MICRO_EXTREME_TOLERANCE = 0.10
    EXHAUSTION_RANGE_RATIO = 1.80
    EXHAUSTION_MIN_RUN = 10

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])

        if len(closed) < 3:
            return {}

        current = closed[-1]
        previous = closed[-2]
        prior = closed[-3]
        reference = closed[-11:-1]

        inside_count = cls._inside_count(closed)
        two_bar_direction = cls._two_bar_reversal(
            previous,
            current,
        )
        three_bar_direction = cls._three_bar_reversal(
            prior,
            previous,
            current,
        )
        ioi = (
            len(closed) >= 4
            and cls._is_inside(closed[-4], closed[-3])
            and cls._is_outside(closed[-3], closed[-2])
            and cls._is_inside(closed[-2], closed[-1])
        )

        typical_range = cls._typical_range(reference)
        tolerance = typical_range * cls.MICRO_EXTREME_TOLERANCE
        micro_double_bottom = (
            abs(current.low - previous.low) <= tolerance
            and cls._direction(previous) != cls._direction(current)
        )
        micro_double_top = (
            abs(current.high - previous.high) <= tolerance
            and cls._direction(previous) != cls._direction(current)
        )

        failed_reversal_direction = cls._failed_reversal(
            closed,
            current,
        )
        shaved_top = current.upper_wick <= 1e-9
        shaved_bottom = current.lower_wick <= 1e-9
        shaved_trend_bar = (
            cls._body_ratio(current) >= cls.TREND_BODY_RATIO
            and (shaved_top or shaved_bottom)
        )
        exhaustion = cls._is_exhaustion(
            closed,
            trend,
            typical_range,
        )

        pattern = cls._primary_pattern(
            failed_reversal_direction=failed_reversal_direction,
            exhaustion=exhaustion,
            three_bar_direction=three_bar_direction,
            two_bar_direction=two_bar_direction,
            ioi=ioi,
            inside_count=inside_count,
            micro_double_bottom=micro_double_bottom,
            micro_double_top=micro_double_top,
            shaved_trend_bar=shaved_trend_bar,
        )
        direction = cls._pattern_direction(
            pattern=pattern,
            current=current,
            two_bar_direction=two_bar_direction,
            three_bar_direction=three_bar_direction,
            failed_reversal_direction=failed_reversal_direction,
            trend=trend,
        )

        return {
            "brooks_composite_pattern": pattern,
            "brooks_composite_direction": direction,
            "brooks_two_bar_reversal": two_bar_direction != "NONE",
            "brooks_two_bar_direction": two_bar_direction,
            "brooks_three_bar_reversal": three_bar_direction != "NONE",
            "brooks_three_bar_direction": three_bar_direction,
            "brooks_inside_sequence_count": inside_count,
            "brooks_ioi_pattern": ioi,
            "brooks_micro_double_bottom": micro_double_bottom,
            "brooks_micro_double_top": micro_double_top,
            "brooks_failed_reversal": failed_reversal_direction != "NONE",
            "brooks_failed_reversal_direction": failed_reversal_direction,
            "brooks_shaved_top": shaved_top,
            "brooks_shaved_bottom": shaved_bottom,
            "brooks_shaved_trend_bar": shaved_trend_bar,
            "brooks_exhaustion_bar": exhaustion,
            "brooks_composite_context": cls._context(direction, trend),
        }

    @classmethod
    def _two_bar_reversal(cls, first, second):
        first_direction = cls._direction(first)
        second_direction = cls._direction(second)

        if (
            first_direction == "NONE"
            or second_direction == "NONE"
            or first_direction == second_direction
            or cls._body_ratio(first) < cls.TREND_BODY_RATIO
            or cls._body_ratio(second) < cls.TREND_BODY_RATIO
        ):
            return "NONE"

        largest = max(first.range, second.range)
        smallest = min(first.range, second.range)
        if largest <= 0.0 or smallest / largest < cls.SIMILAR_RANGE_RATIO:
            return "NONE"

        return "BULL" if second_direction == "BULL" else "BEAR"

    @classmethod
    def _three_bar_reversal(cls, first, middle, third):
        first_direction = cls._direction(first)
        third_direction = cls._direction(third)

        if (
            first_direction == "NONE"
            or third_direction == "NONE"
            or first_direction == third_direction
            or cls._body_ratio(first) < cls.TREND_BODY_RATIO
            or cls._body_ratio(third) < cls.TREND_BODY_RATIO
        ):
            return "NONE"

        middle_is_pause = (
            cls._body_ratio(middle) <= cls.DOJI_BODY_RATIO
            or cls._is_inside(first, middle)
            or middle.range <= (
                max(first.range, third.range)
                * cls.SMALL_RANGE_RATIO
            )
        )
        if not middle_is_pause:
            return "NONE"

        return "BULL" if third_direction == "BULL" else "BEAR"

    @classmethod
    def _inside_count(cls, closed):
        count = 0

        for index in range(len(closed) - 1, 0, -1):
            if not cls._is_inside(closed[index - 1], closed[index]):
                break
            count += 1

        return count

    @staticmethod
    def _is_inside(previous, current):
        return (
            current.high <= previous.high
            and current.low >= previous.low
        )

    @staticmethod
    def _is_outside(previous, current):
        return (
            current.high >= previous.high
            and current.low <= previous.low
            and (
                current.high > previous.high
                or current.low < previous.low
            )
        )

    @classmethod
    def _failed_reversal(cls, closed, current):
        from analysis.price_action.reversal_bar_dynamics import (
            ReversalBarDynamics,
        )

        previous_metrics = ReversalBarDynamics.analyze(
            closed,
            trend=Trend.UNKNOWN,
        )
        previous_direction = previous_metrics.get(
            "brooks_reversal_direction",
            "NONE",
        )

        if previous_direction == "BULL" and current.low < closed[-2].low:
            return "DOWN"
        if previous_direction == "BEAR" and current.high > closed[-2].high:
            return "UP"
        return "NONE"

    @classmethod
    def _is_exhaustion(cls, closed, trend, typical_range):
        if typical_range <= 0.0:
            return False

        current = closed[-1]
        trend_direction = (
            "BULL"
            if trend == Trend.UP
            else "BEAR"
            if trend == Trend.DOWN
            else "NONE"
        )
        if cls._direction(current) != trend_direction:
            return False

        run = 0
        for candle in reversed(closed[:-1]):
            if cls._direction(candle) != trend_direction:
                break
            run += 1

        return (
            run >= cls.EXHAUSTION_MIN_RUN
            and current.range / typical_range >= cls.EXHAUSTION_RANGE_RATIO
        )

    @staticmethod
    def _primary_pattern(
        *,
        failed_reversal_direction,
        exhaustion,
        three_bar_direction,
        two_bar_direction,
        ioi,
        inside_count,
        micro_double_bottom,
        micro_double_top,
        shaved_trend_bar,
    ):
        if exhaustion:
            return "EXHAUSTION_BAR"
        if three_bar_direction != "NONE":
            return "THREE_BAR_REVERSAL"
        if two_bar_direction != "NONE":
            return "TWO_BAR_REVERSAL"
        if failed_reversal_direction != "NONE":
            return "FAILED_REVERSAL"
        if ioi:
            return "IOI"
        if inside_count >= 3:
            return "III"
        if inside_count >= 2:
            return "II"
        if micro_double_bottom:
            return "MICRO_DOUBLE_BOTTOM"
        if micro_double_top:
            return "MICRO_DOUBLE_TOP"
        if shaved_trend_bar:
            return "SHAVED_TREND_BAR"
        return "NONE"

    @classmethod
    def _pattern_direction(
        cls,
        *,
        pattern,
        current,
        two_bar_direction,
        three_bar_direction,
        failed_reversal_direction,
        trend,
    ):
        if pattern == "FAILED_REVERSAL":
            return failed_reversal_direction
        if pattern == "THREE_BAR_REVERSAL":
            return three_bar_direction
        if pattern == "TWO_BAR_REVERSAL":
            return two_bar_direction
        if pattern == "MICRO_DOUBLE_BOTTOM":
            return "UP"
        if pattern == "MICRO_DOUBLE_TOP":
            return "DOWN"
        if pattern in ("II", "III", "IOI"):
            return "BOTH"
        if pattern in ("SHAVED_TREND_BAR", "EXHAUSTION_BAR"):
            return "UP" if cls._direction(current) == "BULL" else "DOWN"
        if trend == Trend.UP:
            return "UP"
        if trend == Trend.DOWN:
            return "DOWN"
        return "NONE"

    @staticmethod
    def _context(direction, trend):
        if direction in ("NONE", "BOTH"):
            return "NEUTRAL"
        if trend == Trend.UP:
            return "WITH_TREND" if direction == "UP" else "COUNTER_TREND"
        if trend == Trend.DOWN:
            return "WITH_TREND" if direction == "DOWN" else "COUNTER_TREND"
        return "NEUTRAL"

    @staticmethod
    def _direction(candle):
        if candle.close > candle.open:
            return "BULL"
        if candle.close < candle.open:
            return "BEAR"
        return "NONE"

    @staticmethod
    def _body_ratio(candle):
        if candle.range <= 0.0:
            return 0.0
        return candle.body / candle.range

    @staticmethod
    def _typical_range(candles):
        ranges = [candle.range for candle in candles if candle.range > 0.0]
        return median(ranges) if ranges else 0.0
