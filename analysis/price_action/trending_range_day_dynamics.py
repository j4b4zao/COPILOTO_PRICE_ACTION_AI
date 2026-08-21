"""Diagnóstico de Trending Trading Range Day inspirado em Brooks Trends, capítulo 22.

A camada é puramente diagnóstica. Ela não autoriza ordens nem altera Score,
Risk ou Decision. O candle atual é excluído da confirmação.
"""

from statistics import median

from enums.trend import Trend


class TrendingRangeDayDynamics:

    LOOKBACK = 30
    OPENING_BARS = 6
    MIN_BARS = 12

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])
        if len(closed) < cls.MIN_BARS:
            return cls._empty()

        window = closed[-cls.LOOKBACK:]
        opening = window[: min(cls.OPENING_BARS, len(window))]
        if len(opening) < 4:
            return cls._empty()

        opening_high = max(c.high for c in opening)
        opening_low = min(c.low for c in opening)
        opening_range = max(opening_high - opening_low, 0.0)

        typical_range = cls._typical_range(window)
        estimated_daily_range = typical_range * max(len(window), 1) ** 0.5
        opening_ratio = (
            opening_range / estimated_daily_range
            if estimated_daily_range > 0.0
            else 0.0
        )

        after_opening = window[len(opening):]
        breakout = cls._find_breakout(after_opening, opening_high, opening_low)

        if breakout is None:
            return cls._base_result(
                opening_high,
                opening_low,
                opening_range,
                opening_ratio,
                estimated_daily_range,
            )

        breakout_index, direction, breakout_price = breakout
        post_breakout = after_opening[breakout_index + 1:]

        second_range = cls._second_range(post_breakout, direction)
        test = cls._test_prior_range(
            post_breakout,
            direction,
            opening_high,
            opening_low,
        )

        breakout_count = cls._count_directional_breakouts(
            window,
            typical_range,
        )

        trend_strength = cls._trend_strength(window, direction)
        multi_breakout_trend = breakout_count >= 2 and trend_strength >= 0.60

        measured_target = (
            opening_high + opening_range
            if direction == "UP"
            else opening_low - opening_range
        )

        current = window[-1]
        measured_target_hit = (
            current.high >= measured_target
            if direction == "UP"
            else current.low <= measured_target
        )

        reversal_risk = bool(test["traversed_prior_range"])

        if reversal_risk:
            state = "REVERSAL_RISK"
        elif second_range["formed"]:
            state = "SECOND_RANGE"
        else:
            state = "BREAKOUT_PHASE"

        direction_bias = "BUY" if direction == "UP" else "SELL"

        if trend in (Trend.UP, Trend.DOWN):
            aligned = (
                trend == Trend.UP and direction == "UP"
            ) or (
                trend == Trend.DOWN and direction == "DOWN"
            )
        else:
            aligned = False

        two_sided = bool(
            second_range["formed"]
            and second_range["opposite_bars"] > 0
            and not multi_breakout_trend
        )

        return {
            "brooks_trending_range_state": state,
            "brooks_trending_range_direction": direction_bias,
            "brooks_trending_range_opening_high": round(opening_high, 4),
            "brooks_trending_range_opening_low": round(opening_low, 4),
            "brooks_trending_range_opening_range": round(opening_range, 4),
            "brooks_trending_range_estimated_daily_range": round(
                estimated_daily_range,
                4,
            ),
            "brooks_trending_range_opening_ratio": round(opening_ratio, 4),
            "brooks_trending_range_opening_ratio_typical": (
                0.25 <= opening_ratio <= 0.60
            ),
            "brooks_trending_range_breakout": True,
            "brooks_trending_range_breakout_direction": direction,
            "brooks_trending_range_breakout_price": round(breakout_price, 4),
            "brooks_trending_range_second_range": second_range["formed"],
            "brooks_trending_range_second_range_high": round(
                second_range["high"],
                4,
            ),
            "brooks_trending_range_second_range_low": round(
                second_range["low"],
                4,
            ),
            "brooks_trending_range_prior_range_tested": test["tested"],
            "brooks_trending_range_prior_range_penetrated": test["penetrated"],
            "brooks_trending_range_prior_range_traversed": test[
                "traversed_prior_range"
            ],
            "brooks_trending_range_breakout_count": breakout_count,
            "brooks_trending_range_multi_breakout_trend": multi_breakout_trend,
            "brooks_trending_range_two_sided": two_sided,
            "brooks_trending_range_measured_target": round(measured_target, 4),
            "brooks_trending_range_measured_target_hit": measured_target_hit,
            "brooks_trending_range_reversal_risk": reversal_risk,
            "brooks_trending_range_aligned_with_structure": aligned,
            "brooks_trending_range_trend_strength": round(trend_strength, 4),
            "brooks_trending_range_valid": True,
        }

    @staticmethod
    def _find_breakout(candles, high, low):
        for index, candle in enumerate(candles):
            if candle.close > high:
                return index, "UP", candle.close
            if candle.close < low:
                return index, "DOWN", candle.close
        return None

    @classmethod
    def _second_range(cls, candles, direction):
        if len(candles) < 4:
            return {
                "formed": False,
                "high": 0.0,
                "low": 0.0,
                "opposite_bars": 0,
            }

        sample = candles[: min(8, len(candles))]
        high = max(c.high for c in sample)
        low = min(c.low for c in sample)
        typical = cls._typical_range(sample)
        total = max(high - low, 0.0)

        opposite_bars = sum(
            1
            for candle in sample
            if (
                direction == "UP" and candle.bearish
            ) or (
                direction == "DOWN" and candle.bullish
            )
        )

        overlap = cls._average_overlap(sample)
        formed = bool(
            typical > 0.0
            and total <= typical * 4.5
            and (opposite_bars >= 1 or overlap >= 0.30)
        )

        return {
            "formed": formed,
            "high": high if formed else 0.0,
            "low": low if formed else 0.0,
            "opposite_bars": opposite_bars,
        }

    @staticmethod
    def _test_prior_range(candles, direction, high, low):
        tested = False
        penetrated = False
        traversed = False

        for candle in candles:
            if direction == "UP":
                if candle.low <= high:
                    tested = True
                if candle.low < high:
                    penetrated = True
                if candle.low <= low:
                    traversed = True
            else:
                if candle.high >= low:
                    tested = True
                if candle.high > low:
                    penetrated = True
                if candle.high >= high:
                    traversed = True

        return {
            "tested": tested,
            "penetrated": penetrated,
            "traversed_prior_range": traversed,
        }

    @classmethod
    def _count_directional_breakouts(cls, candles, typical_range):
        if typical_range <= 0.0 or len(candles) < 3:
            return 0

        count = 0
        threshold = typical_range * 0.75
        for previous, current in zip(candles, candles[1:]):
            if abs(current.close - previous.close) >= threshold:
                count += 1
        return count

    @staticmethod
    def _trend_strength(candles, direction):
        if not candles:
            return 0.0

        aligned = sum(
            1
            for candle in candles
            if (
                direction == "UP" and candle.bullish
            ) or (
                direction == "DOWN" and candle.bearish
            )
        )
        return aligned / len(candles)

    @staticmethod
    def _average_overlap(candles):
        if len(candles) < 2:
            return 0.0

        values = []
        for previous, current in zip(candles, candles[1:]):
            overlap = max(
                0.0,
                min(previous.high, current.high)
                - max(previous.low, current.low),
            )
            base = min(previous.range, current.range)
            values.append(overlap / base if base > 0.0 else 0.0)
        return sum(values) / len(values)

    @staticmethod
    def _typical_range(candles):
        ranges = [c.range for c in candles if c.range > 0.0]
        return median(ranges) if ranges else 0.0

    @classmethod
    def _base_result(
        cls,
        opening_high,
        opening_low,
        opening_range,
        opening_ratio,
        estimated_daily_range,
    ):
        result = cls._empty()
        result.update({
            "brooks_trending_range_state": "OPENING_RANGE",
            "brooks_trending_range_opening_high": round(opening_high, 4),
            "brooks_trending_range_opening_low": round(opening_low, 4),
            "brooks_trending_range_opening_range": round(opening_range, 4),
            "brooks_trending_range_estimated_daily_range": round(
                estimated_daily_range,
                4,
            ),
            "brooks_trending_range_opening_ratio": round(opening_ratio, 4),
            "brooks_trending_range_opening_ratio_typical": (
                0.25 <= opening_ratio <= 0.60
            ),
            "brooks_trending_range_valid": True,
        })
        return result

    @staticmethod
    def _empty():
        return {
            "brooks_trending_range_state": "INSUFFICIENT_DATA",
            "brooks_trending_range_direction": "NONE",
            "brooks_trending_range_opening_high": 0.0,
            "brooks_trending_range_opening_low": 0.0,
            "brooks_trending_range_opening_range": 0.0,
            "brooks_trending_range_estimated_daily_range": 0.0,
            "brooks_trending_range_opening_ratio": 0.0,
            "brooks_trending_range_opening_ratio_typical": False,
            "brooks_trending_range_breakout": False,
            "brooks_trending_range_breakout_direction": "NONE",
            "brooks_trending_range_breakout_price": 0.0,
            "brooks_trending_range_second_range": False,
            "brooks_trending_range_second_range_high": 0.0,
            "brooks_trending_range_second_range_low": 0.0,
            "brooks_trending_range_prior_range_tested": False,
            "brooks_trending_range_prior_range_penetrated": False,
            "brooks_trending_range_prior_range_traversed": False,
            "brooks_trending_range_breakout_count": 0,
            "brooks_trending_range_multi_breakout_trend": False,
            "brooks_trending_range_two_sided": False,
            "brooks_trending_range_measured_target": 0.0,
            "brooks_trending_range_measured_target_hit": False,
            "brooks_trending_range_reversal_risk": False,
            "brooks_trending_range_aligned_with_structure": False,
            "brooks_trending_range_trend_strength": 0.0,
            "brooks_trending_range_valid": False,
        }
