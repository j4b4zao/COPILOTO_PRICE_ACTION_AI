"""
analysis/price_action/opening_range_dynamics.py

Brooks Reversals - Chapter 19 supplemental diagnostics:
Opening Patterns and Reversals / opening range resolution.

Note: the actual Chapter 20 is "Gap Openings: Reversals and Continuations"
and is implemented separately in gap_opening_dynamics.py.

Diagnostic-only layer. It does not alter Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class OpeningRangeResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    range_high: float = 0.0
    range_low: float = 0.0
    range_mid: float = 0.0
    range_size: float = 0.0
    two_sided: bool = False
    breakout_attempt: bool = False
    breakout_confirmed: bool = False
    failed_breakout: bool = False
    retest: bool = False
    follow_through: bool = False
    breakout_mode: bool = False
    reversal_watch: bool = False
    continuation_watch: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class OpeningRangeDynamics:
    """Evaluate the opening range and its first meaningful resolution."""

    RANGE_BARS = 3
    MIN_CLOSED_BARS = 5

    def analyze(self, session_candles):
        candles = list(session_candles or [])
        closed = candles[:-1] if candles else []

        if len(closed) < self.MIN_CLOSED_BARS:
            return OpeningRangeResult(reasons=("INSUFFICIENT_HISTORY",))

        opening = closed[: self.RANGE_BARS]
        later = closed[self.RANGE_BARS :]

        high = max(float(c.high) for c in opening)
        low = min(float(c.low) for c in opening)
        size = high - low
        if size <= 0:
            return OpeningRangeResult(reasons=("INVALID_OPENING_RANGE",))

        mid = (high + low) / 2.0
        bulls = sum(float(c.close) > float(c.open) for c in opening)
        bears = sum(float(c.close) < float(c.open) for c in opening)
        two_sided = bulls > 0 and bears > 0

        result = OpeningRangeResult(
            valid=True,
            status="OPENING_RANGE_ACTIVE",
            range_high=high,
            range_low=low,
            range_mid=mid,
            range_size=size,
            two_sided=two_sided,
            breakout_mode=two_sided,
            quality_score=45.0 if two_sided else 50.0,
            reasons=("OPENING_RANGE_DEFINED",),
        )

        up = self._side(later, high, "BUY", size)
        down = self._side(later, low, "SELL", size)
        chosen = self._choose(up, down)

        if chosen is None:
            if two_sided:
                result.status = "OPENING_RANGE_BREAKOUT_MODE"
                result.reasons = ("OPENING_RANGE_TWO_SIDED", "WAIT_FOR_RESOLUTION")
            return result

        result.direction = chosen["direction"]
        result.breakout_attempt = chosen["attempt"]
        result.breakout_confirmed = chosen["confirmed"]
        result.failed_breakout = chosen["failed"]
        result.retest = chosen["retest"]
        result.follow_through = chosen["follow_through"]
        result.reversal_watch = chosen["failed"]
        result.continuation_watch = chosen["confirmed"] or chosen["retest"]
        result.breakout_mode = not chosen["confirmed"] and not chosen["failed"]

        if chosen["failed"]:
            result.status = "OPENING_RANGE_FAILED_BREAKOUT"
            result.quality_score = 78.0 if chosen["follow_through"] else 68.0
        elif chosen["retest"]:
            result.status = "OPENING_RANGE_BREAKOUT_RETEST"
            result.quality_score = 88.0
        elif chosen["confirmed"]:
            result.status = "OPENING_RANGE_BREAKOUT_CONFIRMED"
            result.quality_score = 82.0
        else:
            result.status = "OPENING_RANGE_BREAKOUT_ATTEMPT"
            result.quality_score = 58.0

        reasons = [result.status]
        if chosen["follow_through"]:
            reasons.append("FOLLOW_THROUGH_PRESENT")
        if chosen["retest"]:
            reasons.append("RETEST_HELD")
        if chosen["failed"]:
            reasons.append("BREAKOUT_RETURNED_INSIDE_RANGE")
        result.reasons = tuple(reasons)
        return result

    @staticmethod
    def _side(bars, level, direction, range_size):
        tolerance = range_size * 0.08
        if direction == "BUY":
            outside = [float(b.close) > level for b in bars]
        else:
            outside = [float(b.close) < level for b in bars]

        indexes = [i for i, value in enumerate(outside) if value]
        attempt = bool(indexes)
        confirmed = follow = failed = retest = False

        if indexes:
            first = indexes[0]
            after = bars[first + 1 :]
            if after:
                if direction == "BUY":
                    follow = any(float(b.close) > level for b in after)
                    returned = any(float(b.close) < level for b in after)
                    retest = follow and any(
                        float(b.low) <= level + tolerance and float(b.close) >= level
                        for b in after
                    )
                else:
                    follow = any(float(b.close) < level for b in after)
                    returned = any(float(b.close) > level for b in after)
                    retest = follow and any(
                        float(b.high) >= level - tolerance and float(b.close) <= level
                        for b in after
                    )
                confirmed = follow and not returned
                failed = returned

        return {
            "direction": direction,
            "attempt": attempt,
            "confirmed": confirmed,
            "failed": failed,
            "retest": retest and confirmed,
            "follow_through": follow,
        }

    @staticmethod
    def _choose(up, down):
        for key in ("failed", "retest", "confirmed", "attempt"):
            if up[key] and not down[key]:
                return up
            if down[key] and not up[key]:
                return down
            if up[key] and down[key]:
                return None
        return None
