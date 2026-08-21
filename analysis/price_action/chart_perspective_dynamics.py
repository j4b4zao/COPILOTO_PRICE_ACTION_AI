"""Perspectivas de gráfico inspiradas em Brooks Trends, capítulo 9."""


class ChartPerspectiveDynamics:

    LOOKBACK = 6
    STRONG_EFFICIENCY = 0.65
    MODERATE_EFFICIENCY = 0.40
    STRONG_CONSISTENCY = 0.75
    MODERATE_CONSISTENCY = 0.60

    @classmethod
    def analyze(cls, candles):
        closed = list(candles[:-1])

        if len(closed) < 4:
            return {}

        window = closed[-cls.LOOKBACK:]
        closes = [candle.close for candle in window]
        direction = cls._direction(closes)
        inverse_direction = cls._inverse_direction(direction)
        efficiency = cls._efficiency(closes)
        consistency = cls._consistency(closes, direction)
        clarity = cls._clarity(efficiency, consistency, direction)
        inverse_consistent = cls._mirrors(direction, inverse_direction)

        return {
            "brooks_perspective_state": cls._state(
                direction,
                clarity,
                inverse_consistent,
            ),
            "brooks_perspective_direction": direction,
            "brooks_perspective_inverse_direction": inverse_direction,
            "brooks_perspective_clarity": clarity,
            "brooks_perspective_efficiency": round(efficiency, 4),
            "brooks_perspective_consistency": round(consistency, 4),
            "brooks_perspective_inverse_consistent": inverse_consistent,
            "brooks_perspective_confirmed": (
                direction in ("UP", "DOWN")
                and clarity in ("STRONG", "MODERATE")
                and inverse_consistent
            ),
        }

    @staticmethod
    def _direction(closes):
        net = closes[-1] - closes[0]
        if net > 0.0:
            return "UP"
        if net < 0.0:
            return "DOWN"
        return "NEUTRAL"

    @staticmethod
    def _inverse_direction(direction):
        if direction == "UP":
            return "DOWN"
        if direction == "DOWN":
            return "UP"
        return "NEUTRAL"

    @staticmethod
    def _efficiency(closes):
        travel = sum(
            abs(current - previous)
            for previous, current in zip(closes, closes[1:])
        )
        if travel <= 0.0:
            return 0.0
        return abs(closes[-1] - closes[0]) / travel

    @staticmethod
    def _consistency(closes, direction):
        moves = [
            current - previous
            for previous, current in zip(closes, closes[1:])
        ]
        if not moves or direction == "NEUTRAL":
            return 0.0
        aligned = sum(
            move > 0.0 if direction == "UP" else move < 0.0
            for move in moves
        )
        return aligned / len(moves)

    @classmethod
    def _clarity(cls, efficiency, consistency, direction):
        if direction == "NEUTRAL":
            return "AMBIGUOUS"
        if (
            efficiency >= cls.STRONG_EFFICIENCY
            and consistency >= cls.STRONG_CONSISTENCY
        ):
            return "STRONG"
        if (
            efficiency >= cls.MODERATE_EFFICIENCY
            and consistency >= cls.MODERATE_CONSISTENCY
        ):
            return "MODERATE"
        return "AMBIGUOUS"

    @staticmethod
    def _mirrors(direction, inverse_direction):
        return (
            (direction == "UP" and inverse_direction == "DOWN")
            or (direction == "DOWN" and inverse_direction == "UP")
            or (
                direction == "NEUTRAL"
                and inverse_direction == "NEUTRAL"
            )
        )

    @staticmethod
    def _state(direction, clarity, inverse_consistent):
        if direction == "NEUTRAL" or clarity == "AMBIGUOUS":
            return "AMBIGUOUS_PERSPECTIVE"
        if inverse_consistent:
            return f"{clarity}_{direction}_CONFIRMED"
        return "PERSPECTIVE_CONFLICT"
