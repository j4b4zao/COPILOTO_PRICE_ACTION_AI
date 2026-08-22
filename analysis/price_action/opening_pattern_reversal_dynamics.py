"""
analysis/price_action/opening_pattern_reversal_dynamics.py

Brooks Reversals - Chapter 19: Opening Patterns and Reversals.
Diagnostic-only layer for opening range, opening drive, breakout failure and reversal.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class OpeningPatternReversalResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    opening_range_high: float = 0.0
    opening_range_low: float = 0.0
    opening_range_size: float = 0.0
    opening_drive: bool = False
    breakout_attempt: bool = False
    breakout_follow_through: bool = False
    failed_breakout: bool = False
    reversal_confirmed: bool = False
    two_sided_open: bool = False
    trend_open_watch: bool = False
    reversal_watch: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class OpeningPatternReversalDynamics:
    """Classify early-session opening patterns using closed candles only."""

    MIN_CLOSED_BARS = 5
    OPENING_RANGE_BARS = 3

    def analyze(self, session_candles):
        candles = list(session_candles or [])
        closed = candles[:-1] if candles else []

        if len(closed) < self.MIN_CLOSED_BARS:
            return OpeningPatternReversalResult(reasons=("INSUFFICIENT_HISTORY",))

        opening = closed[: self.OPENING_RANGE_BARS]
        after = closed[self.OPENING_RANGE_BARS :]

        or_high = max(float(c.high) for c in opening)
        or_low = min(float(c.low) for c in opening)
        or_size = max(or_high - or_low, 0.0)

        if or_size <= 0:
            return OpeningPatternReversalResult(reasons=("INVALID_OPENING_RANGE",))

        up_bars = sum(float(c.close) > float(c.open) for c in opening)
        down_bars = sum(float(c.close) < float(c.open) for c in opening)
        opening_drive_up = up_bars >= 2 and float(opening[-1].close) >= or_low + or_size * 0.70
        opening_drive_down = down_bars >= 2 and float(opening[-1].close) <= or_low + or_size * 0.30
        opening_drive = opening_drive_up or opening_drive_down

        up = self._evaluate_side(after, or_high, or_low, "BUY", or_size)
        down = self._evaluate_side(after, or_high, or_low, "SELL", or_size)
        chosen = self._choose(up, down)

        two_sided = (
            any(float(c.high) > or_high for c in after)
            and any(float(c.low) < or_low for c in after)
        )

        result = OpeningPatternReversalResult(
            valid=True,
            status="OPENING_RANGE_FORMED",
            opening_range_high=or_high,
            opening_range_low=or_low,
            opening_range_size=or_size,
            opening_drive=opening_drive,
            two_sided_open=two_sided,
            reasons=("OPENING_RANGE_FORMED",),
        )

        if chosen is None:
            if two_sided:
                result.status = "OPENING_TWO_SIDED"
                result.quality_score = 45.0
                result.reasons = ("OPENING_TWO_SIDED", "BREAKOUT_MODE_OR_RANGE_RISK")
            elif opening_drive:
                result.status = "OPENING_DRIVE"
                result.direction = "BUY" if opening_drive_up else "SELL"
                result.trend_open_watch = True
                result.quality_score = 62.0
                result.reasons = ("OPENING_DRIVE", "WAIT_FOR_CONTINUATION_OR_FAILURE")
            return result

        result.direction = chosen["direction"]
        result.breakout_attempt = chosen["breakout_attempt"]
        result.breakout_follow_through = chosen["follow_through"]
        result.failed_breakout = chosen["failed_breakout"]
        result.reversal_confirmed = chosen["reversal_confirmed"]
        result.reversal_watch = chosen["failed_breakout"]
        result.trend_open_watch = chosen["follow_through"] and not chosen["failed_breakout"]

        if chosen["reversal_confirmed"]:
            result.status = "OPENING_REVERSAL_CONFIRMED"
            result.quality_score = 90.0
            result.reasons = ("OPENING_BREAKOUT_FAILED", "OPPOSITE_FOLLOW_THROUGH_CONFIRMED")
        elif chosen["failed_breakout"]:
            result.status = "OPENING_FAILED_BREAKOUT"
            result.quality_score = 76.0
            result.reasons = ("OPENING_BREAKOUT_FAILED", "REVERSAL_WATCH")
        elif chosen["follow_through"]:
            result.status = "OPENING_BREAKOUT_CONFIRMED"
            result.quality_score = 82.0
            result.reasons = ("OPENING_BREAKOUT_WITH_FOLLOW_THROUGH", "TREND_OPEN_WATCH")
        else:
            result.status = "OPENING_BREAKOUT_ATTEMPT"
            result.quality_score = 58.0
            result.reasons = ("BREAKOUT_NOT_YET_CONFIRMED",)

        return result

    @staticmethod
    def _evaluate_side(after, or_high, or_low, direction, or_size):
        tolerance = or_size * 0.04
        if direction == "BUY":
            attempts = [i for i, c in enumerate(after) if float(c.close) > or_high]
        else:
            attempts = [i for i, c in enumerate(after) if float(c.close) < or_low]

        breakout_attempt = bool(attempts)
        follow_through = False
        failed_breakout = False
        reversal_confirmed = False
        reversal_direction = "NONE"

        if attempts:
            first = attempts[0]
            later = after[first + 1 :]

            if direction == "BUY":
                follow_through = any(float(c.close) > or_high + tolerance for c in later)
                failed_breakout = any(float(c.close) < or_high for c in later)
                opposite = [c for c in later if float(c.close) < float(c.open)]
                reversal_confirmed = (
                    failed_breakout
                    and len(opposite) >= 2
                    and any(float(c.close) < or_low + or_size * 0.55 for c in opposite)
                )
                reversal_direction = "SELL"
            else:
                follow_through = any(float(c.close) < or_low - tolerance for c in later)
                failed_breakout = any(float(c.close) > or_low for c in later)
                opposite = [c for c in later if float(c.close) > float(c.open)]
                reversal_confirmed = (
                    failed_breakout
                    and len(opposite) >= 2
                    and any(float(c.close) > or_low + or_size * 0.45 for c in opposite)
                )
                reversal_direction = "BUY"

        return {
            "direction": reversal_direction if reversal_confirmed else direction,
            "breakout_attempt": breakout_attempt,
            "follow_through": follow_through,
            "failed_breakout": failed_breakout,
            "reversal_confirmed": reversal_confirmed,
        }

    @staticmethod
    def _choose(up, down):
        for key in ("reversal_confirmed", "failed_breakout", "follow_through", "breakout_attempt"):
            if up[key] and not down[key]:
                return up
            if down[key] and not up[key]:
                return down
            if up[key] and down[key]:
                return None
        return None
