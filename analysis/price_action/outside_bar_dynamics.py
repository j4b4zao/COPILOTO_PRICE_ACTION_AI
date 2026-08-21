"""Contexto informativo de barras externas inspirado em Brooks Trends, capítulo 7."""

from statistics import median

from enums.trend import Trend


class OutsideBarDynamics:

    BALANCED_LOW = 0.35
    BALANCED_HIGH = 0.65
    STRONG_BODY_RATIO = 0.50
    DIRECTIONAL_CLOSE_HIGH = 0.75
    DIRECTIONAL_CLOSE_LOW = 0.25
    LARGE_EXPANSION_RATIO = 1.80
    LOOKBACK = 5

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])

        if len(closed) < 3:
            return {}

        current = closed[-1]
        previous = closed[-2]
        prior = closed[-3]
        reference = closed[-(cls.LOOKBACK + 1):-1]

        detected = cls._is_outside(previous, current)
        previous_detected = cls._is_outside(prior, previous)
        double_outside = detected and previous_detected
        direction = (
            cls._direction(current, previous)
            if detected
            else "NONE"
        )
        close_position = cls._close_position(current)
        body_ratio = cls._body_ratio(current)
        expansion_ratio = cls._expansion_ratio(current, reference)
        balanced = (
            detected
            and cls.BALANCED_LOW
            <= close_position
            <= cls.BALANCED_HIGH
        )
        trapped_side = cls._trapped_side(
            current,
            previous,
            detected,
        )
        range_like = detected and (balanced or double_outside)

        previous_direction = (
            cls._direction(previous, prior)
            if previous_detected
            else "NONE"
        )
        follow_through, failed = cls._outcome(
            current,
            previous,
            previous_direction,
        )
        classification = cls._classification(
            detected=detected,
            direction=direction,
            trapped_side=trapped_side,
            range_like=range_like,
        )
        quality = cls._quality(
            detected=detected,
            direction=direction,
            body_ratio=body_ratio,
            close_position=close_position,
            expansion_ratio=expansion_ratio,
            range_like=range_like,
        )

        return {
            "brooks_outside_detected": detected,
            "brooks_outside_direction": direction,
            "brooks_outside_classification": classification,
            "brooks_outside_quality": quality,
            "brooks_outside_context": cls._context(
                direction,
                trend,
            ),
            "brooks_outside_close_position": round(close_position, 4),
            "brooks_outside_body_ratio": round(body_ratio, 4),
            "brooks_outside_expansion_ratio": round(
                expansion_ratio,
                4,
            ),
            "brooks_outside_balanced": balanced,
            "brooks_outside_range_like": range_like,
            "brooks_outside_trapped_side": trapped_side,
            "brooks_double_outside": double_outside,
            "brooks_outside_follow_through": follow_through,
            "brooks_outside_failed": failed,
        }

    @staticmethod
    def _is_outside(previous, current):
        return (
            current.high > previous.high
            and current.low < previous.low
        )

    @classmethod
    def _direction(cls, current, previous):
        if current.close > previous.high:
            return "UP"
        if current.close < previous.low:
            return "DOWN"

        close_position = cls._close_position(current)
        if cls.BALANCED_LOW <= close_position <= cls.BALANCED_HIGH:
            return "BALANCED"
        if current.close > current.open:
            return "UP"
        if current.close < current.open:
            return "DOWN"
        return "BALANCED"

    @staticmethod
    def _trapped_side(current, previous, detected):
        if not detected:
            return "NONE"
        if current.close > previous.high:
            return "BEARS"
        if current.close < previous.low:
            return "BULLS"
        return "NONE"

    @staticmethod
    def _outcome(current, previous, previous_direction):
        if previous_direction == "UP":
            followed = (
                current.close > previous.close
                and current.close > current.open
            )
            failed = (
                current.close < previous.midpoint
                or current.low < previous.low
            )
            return followed, failed

        if previous_direction == "DOWN":
            followed = (
                current.close < previous.close
                and current.close < current.open
            )
            failed = (
                current.close > previous.midpoint
                or current.high > previous.high
            )
            return followed, failed

        return False, False

    @staticmethod
    def _classification(
        *,
        detected,
        direction,
        trapped_side,
        range_like,
    ):
        if not detected:
            return "NONE"
        if range_like:
            return "RANGE_BAR"
        if trapped_side != "NONE":
            return "REVERSAL_TRAP"
        if direction in ("UP", "DOWN"):
            return "DIRECTIONAL"
        return "RANGE_BAR"

    @classmethod
    def _quality(
        cls,
        *,
        detected,
        direction,
        body_ratio,
        close_position,
        expansion_ratio,
        range_like,
    ):
        if not detected:
            return "NONE"
        if range_like:
            return "BALANCED"
        if expansion_ratio >= cls.LARGE_EXPANSION_RATIO:
            return "RISKY_LARGE"

        directional_close = (
            direction == "UP"
            and close_position >= cls.DIRECTIONAL_CLOSE_HIGH
        ) or (
            direction == "DOWN"
            and close_position <= cls.DIRECTIONAL_CLOSE_LOW
        )

        if body_ratio >= cls.STRONG_BODY_RATIO and directional_close:
            return "STRONG"
        return "MODERATE"

    @staticmethod
    def _context(direction, trend):
        if direction not in ("UP", "DOWN"):
            return "NEUTRAL"
        if trend == Trend.UP:
            return "WITH_TREND" if direction == "UP" else "COUNTER_TREND"
        if trend == Trend.DOWN:
            return "WITH_TREND" if direction == "DOWN" else "COUNTER_TREND"
        return "NEUTRAL"

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

    @staticmethod
    def _expansion_ratio(current, reference):
        ranges = [candle.range for candle in reference if candle.range > 0.0]
        typical = median(ranges) if ranges else 0.0
        if typical <= 0.0:
            return 0.0
        return current.range / typical
