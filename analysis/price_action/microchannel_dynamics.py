"""Microcanais inspirados em Brooks Trends, capítulo 16."""

from enums.trend import Trend


class MicrochannelDynamics:

    MIN_BARS = 3
    STRONG_BARS = 5
    LOOKBACK = 12

    @classmethod
    def analyze(cls, candles, trend):
        closed = list(candles[:-1])
        direction = cls._direction(trend)
        if direction == "NONE" or len(closed) < cls.MIN_BARS:
            return cls._empty(
                "NO_CLEAR_TREND" if direction == "NONE" else "NO_MICROCHANNEL"
            )

        window = closed[-cls.LOOKBACK:]
        active_count = cls._trailing_count(window, direction)
        first_break = False
        channel_bars = window[-active_count:]

        if active_count < cls.MIN_BARS and len(window) > cls.MIN_BARS:
            prior_count = cls._trailing_count(window[:-1], direction)
            if prior_count >= cls.MIN_BARS and cls._breaks(window[-2], window[-1], direction):
                first_break = True
                channel_bars = window[-(prior_count + 1):-1]
                active_count = prior_count

        if active_count < cls.MIN_BARS:
            return cls._empty("NO_MICROCHANNEL")

        quality = cls._quality(channel_bars, direction)
        overlap = cls._overlap(channel_bars)
        strength = (
            "STRONG"
            if active_count >= cls.STRONG_BARS and quality >= 0.60
            else "MODERATE"
        )
        retest_level = (
            max(candle.high for candle in channel_bars)
            if direction == "UP"
            else min(candle.low for candle in channel_bars)
        )

        return {
            "brooks_microchannel_state": (
                "FIRST_BREAK" if first_break else "ACTIVE"
            ),
            "brooks_microchannel_direction": direction,
            "brooks_microchannel_strength": strength,
            "brooks_microchannel_bar_count": active_count,
            "brooks_microchannel_pullback_count": 1 if first_break else 0,
            "brooks_microchannel_quality": round(quality, 4),
            "brooks_microchannel_overlap": round(overlap, 4),
            "brooks_microchannel_first_break": first_break,
            "brooks_microchannel_break_direction": (
                cls._opposite(direction) if first_break else "NONE"
            ),
            "brooks_microchannel_first_break_failure_risk": first_break,
            "brooks_microchannel_retest_level": round(retest_level, 4),
            "brooks_microchannel_active": not first_break,
            "brooks_microchannel_valid": True,
        }

    @staticmethod
    def _direction(trend):
        if trend == Trend.UP:
            return "UP"
        if trend == Trend.DOWN:
            return "DOWN"
        return "NONE"

    @classmethod
    def _trailing_count(cls, candles, direction):
        if not candles:
            return 0
        count = 1
        for previous, current in reversed(list(zip(candles, candles[1:]))):
            if cls._continues(previous, current, direction):
                count += 1
            else:
                break
        return count

    @staticmethod
    def _continues(previous, current, direction):
        if direction == "UP":
            return current.low >= previous.low
        return current.high <= previous.high

    @staticmethod
    def _breaks(previous, current, direction):
        if direction == "UP":
            return current.low < previous.low
        return current.high > previous.high

    @staticmethod
    def _quality(candles, direction):
        scores = []
        for candle in candles:
            if candle.range <= 0.0:
                scores.append(0.0)
                continue
            directional = (
                candle.close >= candle.open
                if direction == "UP"
                else candle.close <= candle.open
            )
            body_ratio = abs(candle.close - candle.open) / candle.range
            scores.append(body_ratio if directional else 0.0)
        return sum(scores) / len(scores) if scores else 0.0

    @staticmethod
    def _overlap(candles):
        ratios = []
        for previous, current in zip(candles, candles[1:]):
            shared = max(
                0.0,
                min(previous.high, current.high)
                - max(previous.low, current.low),
            )
            scale = min(previous.range, current.range)
            ratios.append(shared / scale if scale > 0.0 else 0.0)
        return sum(ratios) / len(ratios) if ratios else 0.0

    @staticmethod
    def _opposite(direction):
        return "DOWN" if direction == "UP" else "UP"

    @staticmethod
    def _empty(state):
        return {
            "brooks_microchannel_state": state,
            "brooks_microchannel_direction": "NONE",
            "brooks_microchannel_strength": "NONE",
            "brooks_microchannel_bar_count": 0,
            "brooks_microchannel_pullback_count": 0,
            "brooks_microchannel_quality": 0.0,
            "brooks_microchannel_overlap": 0.0,
            "brooks_microchannel_first_break": False,
            "brooks_microchannel_break_direction": "NONE",
            "brooks_microchannel_first_break_failure_risk": False,
            "brooks_microchannel_retest_level": 0.0,
            "brooks_microchannel_active": False,
            "brooks_microchannel_valid": False,
        }
