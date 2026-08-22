"""
analysis/price_action/previous_day_pattern_dynamics.py

Brooks Reversals - Chapter 18:
Patterns Related to Yesterday: Breakouts, Breakout Pullbacks, and Failed Breakouts.

Diagnostic-only layer. It does not alter Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class PreviousDayPatternResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    previous_high: float = 0.0
    previous_low: float = 0.0
    previous_close: float = 0.0
    previous_range: float = 0.0
    breakout_level: float = 0.0
    breakout_confirmed: bool = False
    breakout_pullback: bool = False
    failed_breakout: bool = False
    follow_through: bool = False
    reversal_watch: bool = False
    continuation_watch: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class PreviousDayPatternDynamics:
    """Evaluate current-session interaction with prior-day structural levels."""

    MIN_CURRENT_BARS = 3

    def analyze(self, previous_day_candles, current_session_candles):
        prev = list(previous_day_candles or [])
        current = list(current_session_candles or [])

        # Exclude the current/forming candle from confirmation logic.
        closed_current = current[:-1] if current else []

        if not prev or len(closed_current) < self.MIN_CURRENT_BARS:
            return PreviousDayPatternResult(
                reasons=("INSUFFICIENT_HISTORY",),
            )

        previous_high = max(float(c.high) for c in prev)
        previous_low = min(float(c.low) for c in prev)
        previous_close = float(prev[-1].close)
        previous_range = max(previous_high - previous_low, 0.0)

        result = PreviousDayPatternResult(
            valid=True,
            status="PREVIOUS_DAY_LEVELS_READY",
            previous_high=previous_high,
            previous_low=previous_low,
            previous_close=previous_close,
            previous_range=previous_range,
            reasons=("PREVIOUS_DAY_LEVELS_READY",),
        )

        if previous_range <= 0:
            result.valid = False
            result.status = "UNKNOWN"
            result.reasons = ("INVALID_PREVIOUS_DAY_RANGE",)
            return result

        bars = closed_current[-6:]
        tolerance = previous_range * 0.03

        up = self._evaluate_side(
            bars,
            level=previous_high,
            direction="BUY",
            tolerance=tolerance,
        )
        down = self._evaluate_side(
            bars,
            level=previous_low,
            direction="SELL",
            tolerance=tolerance,
        )

        chosen = self._choose(up, down)
        if chosen is None:
            return result

        result.direction = chosen["direction"]
        result.breakout_level = chosen["level"]
        result.breakout_confirmed = chosen["breakout_confirmed"]
        result.breakout_pullback = chosen["breakout_pullback"]
        result.failed_breakout = chosen["failed_breakout"]
        result.follow_through = chosen["follow_through"]
        result.reversal_watch = chosen["failed_breakout"]
        result.continuation_watch = (
            chosen["breakout_confirmed"] or chosen["breakout_pullback"]
        )

        if chosen["failed_breakout"]:
            result.status = "PREVIOUS_DAY_FAILED_BREAKOUT"
            score = 85.0 if chosen["follow_through"] else 72.0
        elif chosen["breakout_pullback"]:
            result.status = "PREVIOUS_DAY_BREAKOUT_PULLBACK"
            score = 88.0
        elif chosen["breakout_confirmed"]:
            result.status = "PREVIOUS_DAY_BREAKOUT_CONFIRMED"
            score = 80.0
        else:
            result.status = "PREVIOUS_DAY_LEVEL_TEST"
            score = 55.0

        reasons = [result.status]
        if chosen["follow_through"]:
            reasons.append("FOLLOW_THROUGH_PRESENT")
        if chosen["failed_breakout"]:
            reasons.append("BREAKOUT_RETURNED_INSIDE_PREVIOUS_RANGE")
        if chosen["breakout_pullback"]:
            reasons.append("RETEST_OF_BROKEN_PREVIOUS_DAY_LEVEL")

        result.quality_score = score
        result.reasons = tuple(reasons)
        return result

    @staticmethod
    def _evaluate_side(bars, *, level, direction, tolerance):
        if direction == "BUY":
            closes_out = [float(b.close) > level for b in bars]
            breakout_indexes = [i for i, v in enumerate(closes_out) if v]
        else:
            closes_out = [float(b.close) < level for b in bars]
            breakout_indexes = [i for i, v in enumerate(closes_out) if v]

        touched = any(
            float(b.high) >= level - tolerance
            and float(b.low) <= level + tolerance
            for b in bars
        )

        breakout_confirmed = False
        follow_through = False
        breakout_pullback = False
        failed_breakout = False

        if breakout_indexes:
            first = breakout_indexes[0]
            after = bars[first + 1:]

            if after:
                if direction == "BUY":
                    follow_through = any(float(b.close) > level for b in after)
                    returned_inside = any(float(b.close) < level for b in after)
                    retested = any(
                        float(b.low) <= level + tolerance
                        and float(b.close) >= level
                        for b in after
                    )
                else:
                    follow_through = any(float(b.close) < level for b in after)
                    returned_inside = any(float(b.close) > level for b in after)
                    retested = any(
                        float(b.high) >= level - tolerance
                        and float(b.close) <= level
                        for b in after
                    )

                breakout_confirmed = follow_through and not returned_inside
                breakout_pullback = breakout_confirmed and retested
                failed_breakout = returned_inside

        return {
            "direction": direction,
            "level": level,
            "touched": touched,
            "breakout_confirmed": breakout_confirmed,
            "breakout_pullback": breakout_pullback,
            "failed_breakout": failed_breakout,
            "follow_through": follow_through,
        }

    @staticmethod
    def _choose(up, down):
        priority = (
            "failed_breakout",
            "breakout_pullback",
            "breakout_confirmed",
            "touched",
        )

        for key in priority:
            if up[key] and not down[key]:
                return up
            if down[key] and not up[key]:
                return down
            if up[key] and down[key]:
                # Ambiguous two-sided action: prefer no directional conclusion.
                return None

        return None
