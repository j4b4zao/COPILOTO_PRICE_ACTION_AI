"""Leitura de escadas / broad channel inspirada em Brooks Trends, capítulo 26.

A camada é puramente diagnóstica: reconhece tendências em canal amplo nas quais
os rompimentos são seguidos por retrações profundas e testes frequentes dos
níveis anteriores. Ela não autoriza ordens e não altera Score/Risk/Decision.
"""

from statistics import median

from enums.trend import Trend


class BroadChannelDynamics:

    LOOKBACK = 30
    MIN_SWINGS = 4
    DEEP_PULLBACK_RATIO = 0.45
    VERY_DEEP_PULLBACK_RATIO = 0.70
    TEST_TOLERANCE_RATIO = 0.20

    @classmethod
    def analyze(cls, candles, trend):
        closed = list(candles[:-1])
        if len(closed) < 8 or trend not in (Trend.UP, Trend.DOWN):
            return cls._empty()

        window = closed[-cls.LOOKBACK:]
        tolerance = cls._typical_range(window) * cls.TEST_TOLERANCE_RATIO
        swings = cls._compress_swings(cls._swings(window))
        direction = cls._direction(trend)

        if len(swings) < cls.MIN_SWINGS:
            return cls._empty(direction)

        pullbacks = cls._pullbacks(swings, trend)
        if not pullbacks:
            return cls._empty(direction)

        step_count = cls._step_count(swings, trend)
        breakout_count = step_count
        test_count = cls._prior_level_tests(window, swings, trend, tolerance)
        deep_count = sum(
            1 for item in pullbacks if item >= cls.DEEP_PULLBACK_RATIO
        )
        very_deep_count = sum(
            1 for item in pullbacks if item >= cls.VERY_DEEP_PULLBACK_RATIO
        )
        average_pullback = sum(pullbacks) / len(pullbacks)
        maximum_pullback = max(pullbacks)
        overlap = cls._body_overlap(window)
        two_sided = overlap >= 0.35 or deep_count >= 2

        valid = bool(
            breakout_count >= 2
            and step_count >= 2
            and deep_count >= 1
            and test_count >= 1
        )
        failed_breakout_risk = cls._failed_breakout_risk(
            window,
            swings,
            trend,
            tolerance,
        )
        resumption_bias = bool(
            valid
            and not failed_breakout_risk
            and cls._last_leg_aligned(window, trend)
        )

        if valid and very_deep_count >= 2:
            state = "BROAD_CHANNEL_EXTREME"
            quality = "LOW"
        elif valid and failed_breakout_risk:
            state = "BROAD_CHANNEL_REVERSAL_RISK"
            quality = "MEDIUM"
        elif valid:
            state = "BROAD_CHANNEL"
            quality = "HIGH"
        elif deep_count >= 1 and breakout_count >= 1:
            state = "STAIR_TREND_CANDIDATE"
            quality = "MEDIUM"
        else:
            state = "NORMAL_TREND"
            quality = "LOW"

        return {
            "brooks_broad_channel_state": state,
            "brooks_broad_channel_direction": direction,
            "brooks_broad_channel_quality": quality,
            "brooks_broad_channel_swing_count": len(swings),
            "brooks_broad_channel_step_count": step_count,
            "brooks_broad_channel_breakout_count": breakout_count,
            "brooks_broad_channel_test_count": test_count,
            "brooks_broad_channel_pullback_count": len(pullbacks),
            "brooks_broad_channel_deep_pullback_count": deep_count,
            "brooks_broad_channel_very_deep_pullback_count": very_deep_count,
            "brooks_broad_channel_avg_pullback_ratio": round(average_pullback, 4),
            "brooks_broad_channel_max_pullback_ratio": round(maximum_pullback, 4),
            "brooks_broad_channel_overlap": round(overlap, 4),
            "brooks_broad_channel_tolerance": round(tolerance, 4),
            "brooks_broad_channel_two_sided": two_sided,
            "brooks_broad_channel_failed_breakout_risk": failed_breakout_risk,
            "brooks_broad_channel_resumption_bias": resumption_bias,
            "brooks_broad_channel_valid": valid,
        }

    @staticmethod
    def _swings(candles):
        swings = []
        for index in range(1, len(candles) - 1):
            previous = candles[index - 1]
            current = candles[index]
            following = candles[index + 1]
            if current.high >= previous.high and current.high > following.high:
                swings.append({"type": "HIGH", "price": current.high, "index": index})
            if current.low <= previous.low and current.low < following.low:
                swings.append({"type": "LOW", "price": current.low, "index": index})
        return sorted(swings, key=lambda item: item["index"])

    @staticmethod
    def _compress_swings(swings):
        compressed = []
        for item in swings:
            if not compressed or item["type"] != compressed[-1]["type"]:
                compressed.append(item)
                continue
            more_extreme = (
                item["price"] > compressed[-1]["price"]
                if item["type"] == "HIGH"
                else item["price"] < compressed[-1]["price"]
            )
            if more_extreme:
                compressed[-1] = item
        return compressed

    @staticmethod
    def _step_count(swings, trend):
        point_type = "HIGH" if trend == Trend.UP else "LOW"
        points = [item for item in swings if item["type"] == point_type]
        count = 0
        for previous, current in zip(points, points[1:]):
            if trend == Trend.UP and current["price"] > previous["price"]:
                count += 1
            elif trend == Trend.DOWN and current["price"] < previous["price"]:
                count += 1
        return count

    @staticmethod
    def _pullbacks(swings, trend):
        results = []
        if trend == Trend.UP:
            highs = [item for item in swings if item["type"] == "HIGH"]
            lows = [item for item in swings if item["type"] == "LOW"]
            for high in highs:
                previous_lows = [item for item in lows if item["index"] < high["index"]]
                future_lows = [item for item in lows if item["index"] > high["index"]]
                if not previous_lows or not future_lows:
                    continue
                origin = previous_lows[-1]
                pullback = future_lows[0]
                impulse = high["price"] - origin["price"]
                if impulse > 0:
                    results.append((high["price"] - pullback["price"]) / impulse)
        else:
            lows = [item for item in swings if item["type"] == "LOW"]
            highs = [item for item in swings if item["type"] == "HIGH"]
            for low in lows:
                previous_highs = [item for item in highs if item["index"] < low["index"]]
                future_highs = [item for item in highs if item["index"] > low["index"]]
                if not previous_highs or not future_highs:
                    continue
                origin = previous_highs[-1]
                pullback = future_highs[0]
                impulse = origin["price"] - low["price"]
                if impulse > 0:
                    results.append((pullback["price"] - low["price"]) / impulse)
        return results

    @staticmethod
    def _prior_level_tests(candles, swings, trend, tolerance):
        point_type = "HIGH" if trend == Trend.UP else "LOW"
        points = [item for item in swings if item["type"] == point_type]
        count = 0
        for previous, current in zip(points, points[1:]):
            segment = candles[previous["index"] + 1: current["index"] + 1]
            if trend == Trend.UP:
                tested = any(candle.low <= previous["price"] + tolerance for candle in segment)
            else:
                tested = any(candle.high >= previous["price"] - tolerance for candle in segment)
            if tested:
                count += 1
        return count

    @staticmethod
    def _failed_breakout_risk(candles, swings, trend, tolerance):
        point_type = "HIGH" if trend == Trend.UP else "LOW"
        points = [item for item in swings if item["type"] == point_type]
        if len(points) < 2:
            return False

        previous = points[-2]
        current = points[-1]
        tail = candles[current["index"]:]
        if trend == Trend.UP:
            broke = current["price"] > previous["price"]
            returned = any(candle.close < previous["price"] - tolerance for candle in tail)
        else:
            broke = current["price"] < previous["price"]
            returned = any(candle.close > previous["price"] + tolerance for candle in tail)
        return broke and returned

    @staticmethod
    def _last_leg_aligned(candles, trend):
        recent = candles[-3:]
        if len(recent) < 3:
            return False
        if trend == Trend.UP:
            return sum(candle.bullish for candle in recent) >= 2
        return sum(candle.bearish for candle in recent) >= 2

    @staticmethod
    def _body_overlap(candles):
        values = []
        for first, second in zip(candles, candles[1:]):
            first_low, first_high = sorted((first.open, first.close))
            second_low, second_high = sorted((second.open, second.close))
            overlap = max(0.0, min(first_high, second_high) - max(first_low, second_low))
            union = max(first_high, second_high) - min(first_low, second_low)
            values.append(overlap / union if union > 0 else 0.0)
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _typical_range(candles):
        ranges = [candle.range for candle in candles if candle.range > 0]
        return median(ranges) if ranges else 0.0

    @staticmethod
    def _direction(trend):
        if trend == Trend.UP:
            return "BUY"
        if trend == Trend.DOWN:
            return "SELL"
        return "NONE"

    @staticmethod
    def _empty(direction="NONE"):
        return {
            "brooks_broad_channel_state": "NO_BROAD_CHANNEL",
            "brooks_broad_channel_direction": direction,
            "brooks_broad_channel_quality": "NONE",
            "brooks_broad_channel_swing_count": 0,
            "brooks_broad_channel_step_count": 0,
            "brooks_broad_channel_breakout_count": 0,
            "brooks_broad_channel_test_count": 0,
            "brooks_broad_channel_pullback_count": 0,
            "brooks_broad_channel_deep_pullback_count": 0,
            "brooks_broad_channel_very_deep_pullback_count": 0,
            "brooks_broad_channel_avg_pullback_ratio": 0.0,
            "brooks_broad_channel_max_pullback_ratio": 0.0,
            "brooks_broad_channel_overlap": 0.0,
            "brooks_broad_channel_tolerance": 0.0,
            "brooks_broad_channel_two_sided": False,
            "brooks_broad_channel_failed_breakout_risk": False,
            "brooks_broad_channel_resumption_bias": False,
            "brooks_broad_channel_valid": False,
        }
