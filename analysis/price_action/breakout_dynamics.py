"""Ciclo informativo de rompimentos inspirado em Brooks Trends, capítulo 3."""


class BreakoutDynamics:

    MIN_BASE_CANDLES = 3

    @classmethod
    def analyze(cls, candles):
        closed = list(candles[:-1])

        if len(closed) < cls.MIN_BASE_CANDLES + 1:
            return {}

        previous_breakout = cls._previous_breakout(closed)

        if previous_breakout:
            return cls._classify_follow_through(
                *previous_breakout,
                current=closed[-1],
            )

        return cls._classify_new_breakout(closed)

    @classmethod
    def _previous_breakout(cls, closed):
        base = closed[:-2]

        if len(base) < cls.MIN_BASE_CANDLES:
            return None

        breakout_bar = closed[-2]
        range_high = max(candle.high for candle in base)
        range_low = min(candle.low for candle in base)

        if breakout_bar.close > range_high:
            return (
                "UP",
                range_high,
                breakout_bar,
            )

        if breakout_bar.close < range_low:
            return (
                "DOWN",
                range_low,
                breakout_bar,
            )

        return None

    @classmethod
    def _classify_new_breakout(cls, closed):
        base = closed[:-1]
        current = closed[-1]
        range_high = max(candle.high for candle in base)
        range_low = min(candle.low for candle in base)

        if current.close > range_high:
            return cls._result(
                phase="BREAKOUT_PENDING",
                direction="UP",
                level=range_high,
                breakout_bar=current,
                current=current,
            )

        if current.close < range_low:
            return cls._result(
                phase="BREAKOUT_PENDING",
                direction="DOWN",
                level=range_low,
                breakout_bar=current,
                current=current,
            )

        return cls._empty_result(
            max(candle.high for candle in closed),
            min(candle.low for candle in closed),
        )

    @classmethod
    def _classify_follow_through(
        cls,
        direction,
        level,
        breakout_bar,
        current,
    ):
        if direction == "UP":
            failed = current.close < level
            tested = (
                current.low <= level
                and current.close >= level
            )
            followed = (
                current.close > breakout_bar.close
                and current.close > current.open
            )
        else:
            failed = current.close > level
            tested = (
                current.high >= level
                and current.close <= level
            )
            followed = (
                current.close < breakout_bar.close
                and current.close < current.open
            )

        if failed:
            phase = "BREAKOUT_FAILED"
        elif tested:
            phase = "BREAKOUT_TESTED"
        elif followed:
            phase = "BREAKOUT_CONFIRMED"
        else:
            phase = "BREAKOUT_PENDING"

        return cls._result(
            phase=phase,
            direction=direction,
            level=level,
            breakout_bar=breakout_bar,
            current=current,
        )

    @staticmethod
    def _result(
        *,
        phase,
        direction,
        level,
        breakout_bar,
        current,
    ):
        if direction == "UP":
            penetration = max(
                0.0,
                breakout_bar.close - level,
            )
            distance = current.close - level
        else:
            penetration = max(
                0.0,
                level - breakout_bar.close,
            )
            distance = level - current.close

        return {
            "brooks_breakout_phase": phase,
            "brooks_breakout_direction": direction,
            "brooks_breakout_level": float(level),
            "brooks_breakout_penetration": round(
                penetration,
                4,
            ),
            "brooks_breakout_distance": round(
                distance,
                4,
            ),
            "brooks_breakout_follow_through": (
                phase == "BREAKOUT_CONFIRMED"
            ),
            "brooks_breakout_tested": (
                phase == "BREAKOUT_TESTED"
            ),
            "brooks_breakout_failed": (
                phase == "BREAKOUT_FAILED"
            ),
        }

    @staticmethod
    def _empty_result(range_high, range_low):
        return {
            "brooks_breakout_phase": "RANGE",
            "brooks_breakout_direction": "NONE",
            "brooks_breakout_level": 0.0,
            "brooks_breakout_penetration": 0.0,
            "brooks_breakout_distance": 0.0,
            "brooks_breakout_follow_through": False,
            "brooks_breakout_tested": False,
            "brooks_breakout_failed": False,
            "brooks_range_high": float(range_high),
            "brooks_range_low": float(range_low),
        }
