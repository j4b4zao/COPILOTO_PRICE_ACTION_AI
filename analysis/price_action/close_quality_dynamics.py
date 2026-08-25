"""Qualidade informativa do fechamento inspirada em Brooks Trends, capítulo 8."""

from enums.trend import Trend


class CloseQualityDynamics:

    STRONG_HIGH = 0.75
    STRONG_LOW = 0.25
    MID_LOW = 0.40
    MID_HIGH = 0.60
    MIN_BODY_RATIO = 0.30
    LOOKBACK = 5

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])

        if len(closed) < 2:
            return {}

        current = closed[-1]
        previous = closed[-2]
        reference = closed[-(cls.LOOKBACK + 1):-1]

        close_position = cls._close_position(current)
        body_ratio = cls._body_ratio(current)
        direction = cls._direction(close_position)
        near_extreme = direction in ("UP", "DOWN")
        quality = cls._quality(
            direction,
            close_position,
            body_ratio,
        )
        progress = cls._progress(current, previous)
        reversed_closes = cls._reversed_closes(
            current,
            reference,
            direction,
        )
        consistency = cls._consistency(closed, direction)
        follow_through = cls._follow_through(
            current,
            previous,
            direction,
        )
        deterioration = cls._deterioration(
            current,
            previous,
            close_position,
        )

        return {
            "brooks_close_state": cls._state(direction, quality),
            "brooks_close_direction": direction,
            "brooks_close_quality": quality,
            "brooks_close_context": cls._context(direction, trend),
            "brooks_close_position": round(close_position, 4),
            "brooks_close_distance_to_extreme": round(
                cls._distance_to_extreme(close_position, direction),
                4,
            ),
            "brooks_close_body_ratio": round(body_ratio, 4),
            "brooks_close_progress": round(progress, 4),
            "brooks_close_reversed_closes": reversed_closes,
            "brooks_close_consistency": consistency,
            "brooks_close_near_extreme": near_extreme,
            "brooks_close_follow_through": follow_through,
            "brooks_close_deterioration": deterioration,
            "brooks_close_confirmed": quality in ("STRONG", "MODERATE"),
        }

    @classmethod
    def _direction(cls, close_position):
        if close_position >= cls.STRONG_HIGH:
            return "UP"
        if close_position <= cls.STRONG_LOW:
            return "DOWN"
        return "NEUTRAL"

    @classmethod
    def _quality(cls, direction, close_position, body_ratio):
        if direction == "NEUTRAL":
            return "MID_RANGE"
        if body_ratio >= cls.MIN_BODY_RATIO:
            return "STRONG"
        return "MODERATE"

    @staticmethod
    def _state(direction, quality):
        if direction == "UP":
            return f"{quality}_BULL_CLOSE"
        if direction == "DOWN":
            return f"{quality}_BEAR_CLOSE"
        return "MID_RANGE_CLOSE"

    @staticmethod
    def _progress(current, previous):
        scale = max(current.range, previous.range)
        if scale <= 0.0:
            return 0.0
        return (current.close - previous.close) / scale

    @staticmethod
    def _reversed_closes(current, reference, direction):
        if direction == "UP":
            return sum(current.close > candle.close for candle in reference)
        if direction == "DOWN":
            return sum(current.close < candle.close for candle in reference)
        return 0

    @classmethod
    def _consistency(cls, closed, direction):
        if direction not in ("UP", "DOWN"):
            return 0

        count = 0
        for candle in reversed(closed):
            candle_direction = cls._direction(cls._close_position(candle))
            if candle_direction != direction:
                break
            count += 1
        return count

    @classmethod
    def _follow_through(cls, current, previous, direction):
        previous_direction = cls._direction(
            cls._close_position(previous)
        )
        if direction != previous_direction:
            return False
        if direction == "UP":
            return current.close > previous.close
        if direction == "DOWN":
            return current.close < previous.close
        return False

    @classmethod
    def _deterioration(
        cls,
        current,
        previous,
        current_close_position,
    ):
        previous_direction = cls._direction(
            cls._close_position(previous)
        )
        if previous_direction == "UP":
            return (
                current.close <= previous.close
                and current_close_position < cls.STRONG_HIGH
            )
        if previous_direction == "DOWN":
            return (
                current.close >= previous.close
                and current_close_position > cls.STRONG_LOW
            )
        return False

    @staticmethod
    def _context(direction, trend):
        if direction == "NEUTRAL":
            return "NEUTRAL"
        if trend == Trend.UP:
            return "WITH_TREND" if direction == "UP" else "COUNTER_TREND"
        if trend == Trend.DOWN:
            return "WITH_TREND" if direction == "DOWN" else "COUNTER_TREND"
        return "NEUTRAL"

    @staticmethod
    def _distance_to_extreme(close_position, direction):
        if direction == "UP":
            return 1.0 - close_position
        if direction == "DOWN":
            return close_position
        return min(close_position, 1.0 - close_position)

    @staticmethod
    def _close_position(candle):
        if candle.range <= 0.0:
            return 0.5
        return (candle.close - candle.low) / candle.range

    @staticmethod
    def _body_ratio(candle):
        if candle.range <= 0.0:
            return 0.0
        return candle.body / candle.range
