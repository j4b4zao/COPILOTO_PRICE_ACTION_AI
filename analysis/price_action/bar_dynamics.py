"""Leitura informativa de barras inspirada em Brooks Trends, capítulo 2."""

from statistics import median


class BarDynamics:

    DOJI_BODY_RATIO = 0.10
    MODERATE_BODY_RATIO = 0.30
    STRONG_BODY_RATIO = 0.60
    PROMINENT_TAIL_RATIO = 0.35

    @classmethod
    def analyze(cls, candles):
        closed = list(candles[:-1])

        if len(closed) < 2:
            return {}

        current = closed[-1]
        previous = closed[-2]
        reference = closed[-6:-1]

        body_ratio = cls._body_ratio(current)
        direction = cls._direction(current)
        classification = (
            "DOJI"
            if body_ratio <= cls.DOJI_BODY_RATIO
            else "TREND_BAR"
        )
        reference_bodies = [
            candle.body
            for candle in reference
        ]
        median_body = (
            median(reference_bodies)
            if reference_bodies
            else 0.0
        )
        relative_body_ratio = (
            current.body / median_body
            if median_body > 0.0
            else 0.0
        )
        close_position = cls._close_position(current)

        strength = cls._strength(
            classification,
            direction,
            body_ratio,
            relative_body_ratio,
            close_position,
        )

        pause_detected = cls._is_pause(
            previous,
            current,
            classification,
            direction,
        )

        if pause_detected:
            climax_direction = cls._direction(previous)
            climax_length = cls._run_length(
                closed[:-1],
                climax_direction,
            )
            climax_active = False
            climax_ended = climax_length > 0
        else:
            climax_direction = direction
            climax_length = cls._run_length(
                closed,
                direction,
            )
            climax_active = (
                classification == "TREND_BAR"
                and climax_length > 0
            )
            climax_ended = False

        return {
            "bar_classification": classification,
            "bar_direction": direction,
            "body_ratio": round(body_ratio, 4),
            "relative_body_ratio": round(
                relative_body_ratio,
                4,
            ),
            "close_position": round(close_position, 4),
            "trend_bar_strength": strength,
            "climax_direction": climax_direction,
            "climax_length": climax_length,
            "climax_active": climax_active,
            "climax_ended": climax_ended,
            "pause_detected": pause_detected,
        }

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
    def _close_position(candle):
        if candle.range <= 0.0:
            return 0.5
        return (candle.close - candle.low) / candle.range

    @classmethod
    def _strength(
        cls,
        classification,
        direction,
        body_ratio,
        relative_body_ratio,
        close_position,
    ):
        if classification == "DOJI":
            return "DOJI"

        directional_close = (
            direction == "BULL"
            and close_position >= 0.75
        ) or (
            direction == "BEAR"
            and close_position <= 0.25
        )

        if (
            body_ratio >= cls.STRONG_BODY_RATIO
            and relative_body_ratio >= 1.0
            and directional_close
        ):
            return "STRONG"

        if body_ratio >= cls.MODERATE_BODY_RATIO:
            return "MODERATE"

        return "WEAK"

    @classmethod
    def _is_pause(
        cls,
        previous,
        current,
        classification,
        direction,
    ):
        previous_direction = cls._direction(previous)

        if previous_direction == "NONE":
            return False

        inside_bar = (
            current.high < previous.high
            and current.low > previous.low
        )
        prominent_tail = (
            current.range > 0.0
            and max(
                current.upper_wick,
                current.lower_wick,
            ) / current.range >= cls.PROMINENT_TAIL_RATIO
        )
        opposite_bar = (
            direction not in ("NONE", previous_direction)
        )

        return (
            classification == "DOJI"
            or inside_bar
            or prominent_tail
            or opposite_bar
        )

    @classmethod
    def _run_length(cls, candles, direction):
        if direction not in ("BULL", "BEAR"):
            return 0

        length = 0

        for candle in reversed(candles):
            if (
                cls._direction(candle) != direction
                or cls._body_ratio(candle) <= cls.DOJI_BODY_RATIO
            ):
                break
            length += 1

        return length
