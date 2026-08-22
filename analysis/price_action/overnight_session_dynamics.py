"""
analysis/price_action/overnight_session_dynamics.py

Brooks Reversals - Chapter 14:
Globex, Premarket, Postmarket and Overnight Market.

Diagnostic-only layer for extended-session reference levels.
The overnight session creates context and price magnets; it does not
create a trade signal by itself.

This module does not alter Score, Risk, Decision or order execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class OvernightSessionResult:
    valid: bool = False
    status: str = "UNKNOWN"
    overnight_high: float = 0.0
    overnight_low: float = 0.0
    overnight_open: float = 0.0
    overnight_close: float = 0.0
    overnight_range: float = 0.0
    overnight_direction: str = "NEUTRAL"
    regular_open: float = 0.0
    opening_location: str = "UNKNOWN"
    gap_points: float = 0.0
    gap_ratio: float = 0.0
    level_signal: str = "NONE"
    overnight_high_tested: bool = False
    overnight_low_tested: bool = False
    overnight_high_rejected: bool = False
    overnight_low_rejected: bool = False
    overnight_high_breakout: bool = False
    overnight_low_breakout: bool = False
    follow_through: bool = False
    breakout_confirmed: bool = False
    reversal_watch: bool = False
    breakout_watch: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class OvernightSessionDynamics:
    """Evaluate extended-session levels and the regular-session reaction."""

    MIN_OVERNIGHT_BARS = 3

    def analyze(
        self,
        overnight_candles,
        regular_candles=None,
        *,
        tick_size=1.0,
        exclude_current=True,
    ):
        overnight = list(overnight_candles or [])
        regular = list(regular_candles or [])

        if exclude_current:
            if overnight:
                overnight = overnight[:-1]
            if regular:
                regular = regular[:-1]

        if len(overnight) < self.MIN_OVERNIGHT_BARS:
            return OvernightSessionResult(
                reasons=("INSUFFICIENT_OVERNIGHT_HISTORY",),
            )

        overnight_high = max(float(c.high) for c in overnight)
        overnight_low = min(float(c.low) for c in overnight)
        overnight_open = float(overnight[0].open)
        overnight_close = float(overnight[-1].close)
        overnight_range = max(overnight_high - overnight_low, 0.0)

        if overnight_close > overnight_open:
            overnight_direction = "BULLISH"
        elif overnight_close < overnight_open:
            overnight_direction = "BEARISH"
        else:
            overnight_direction = "NEUTRAL"

        if not regular:
            return OvernightSessionResult(
                valid=True,
                status="OVERNIGHT_LEVELS_READY",
                overnight_high=overnight_high,
                overnight_low=overnight_low,
                overnight_open=overnight_open,
                overnight_close=overnight_close,
                overnight_range=overnight_range,
                overnight_direction=overnight_direction,
                breakout_watch=True,
                reversal_watch=True,
                quality_score=45.0,
                reasons=(
                    "OVERNIGHT_HIGH_LOW_ARE_REFERENCE_LEVELS",
                    "WAIT_FOR_REGULAR_SESSION_PRICE_ACTION",
                ),
            )

        regular_open = float(regular[0].open)
        tolerance = max(float(tick_size or 0.0) * 2.0, overnight_range * 0.03)

        if regular_open > overnight_high:
            opening_location = "ABOVE_OVERNIGHT_RANGE"
            gap_points = regular_open - overnight_high
        elif regular_open < overnight_low:
            opening_location = "BELOW_OVERNIGHT_RANGE"
            gap_points = regular_open - overnight_low
        else:
            opening_location = "INSIDE_OVERNIGHT_RANGE"
            gap_points = 0.0

        gap_ratio = (
            abs(gap_points) / overnight_range
            if overnight_range > 0
            else 0.0
        )

        high_tested = any(float(c.high) >= overnight_high - tolerance for c in regular)
        low_tested = any(float(c.low) <= overnight_low + tolerance for c in regular)

        high_rejected = any(
            float(c.high) > overnight_high
            and float(c.close) < overnight_high
            for c in regular
        )
        low_rejected = any(
            float(c.low) < overnight_low
            and float(c.close) > overnight_low
            for c in regular
        )

        high_breakout_indices = [
            i for i, c in enumerate(regular)
            if float(c.close) > overnight_high
        ]
        low_breakout_indices = [
            i for i, c in enumerate(regular)
            if float(c.close) < overnight_low
        ]

        high_breakout = bool(high_breakout_indices)
        low_breakout = bool(low_breakout_indices)

        high_follow = self._has_follow_through(
            regular,
            high_breakout_indices,
            overnight_high,
            direction="UP",
        )
        low_follow = self._has_follow_through(
            regular,
            low_breakout_indices,
            overnight_low,
            direction="DOWN",
        )

        breakout_confirmed = high_follow or low_follow
        follow_through = breakout_confirmed

        if high_follow:
            status = "OVERNIGHT_HIGH_BREAKOUT_CONFIRMED"
            level_signal = "BUY_BREAKOUT"
        elif low_follow:
            status = "OVERNIGHT_LOW_BREAKOUT_CONFIRMED"
            level_signal = "SELL_BREAKOUT"
        elif high_rejected:
            status = "OVERNIGHT_HIGH_REJECTION"
            level_signal = "SELL_REJECTION"
        elif low_rejected:
            status = "OVERNIGHT_LOW_REJECTION"
            level_signal = "BUY_REJECTION"
        elif high_breakout or low_breakout:
            status = "OVERNIGHT_BREAKOUT_ATTEMPT"
            level_signal = "BREAKOUT_WAIT_FOLLOW_THROUGH"
        elif high_tested or low_tested:
            status = "OVERNIGHT_LEVEL_TEST"
            level_signal = "LEVEL_TEST_ONLY"
        else:
            status = "REGULAR_SESSION_INSIDE_OVERNIGHT_CONTEXT"
            level_signal = "NONE"

        reversal_watch = high_rejected or low_rejected or high_tested or low_tested
        breakout_watch = (
            high_breakout
            or low_breakout
            or opening_location != "INSIDE_OVERNIGHT_RANGE"
        )

        score = 30.0
        if high_tested or low_tested:
            score += 15.0
        if high_rejected or low_rejected:
            score += 25.0
        if high_breakout or low_breakout:
            score += 15.0
        if breakout_confirmed:
            score += 20.0
        if opening_location != "INSIDE_OVERNIGHT_RANGE":
            score += min(10.0, gap_ratio * 10.0)
        score = min(score, 100.0)

        reasons = [
            f"OVERNIGHT_DIRECTION_{overnight_direction}",
            f"OPENING_LOCATION_{opening_location}",
            "OVERNIGHT_HIGH_LOW_TREATED_AS_REFERENCE_LEVELS",
        ]

        if high_rejected:
            reasons.append("FAILED_BREAK_ABOVE_OVERNIGHT_HIGH")
        if low_rejected:
            reasons.append("FAILED_BREAK_BELOW_OVERNIGHT_LOW")
        if high_breakout:
            reasons.append("CLOSE_ABOVE_OVERNIGHT_HIGH")
        if low_breakout:
            reasons.append("CLOSE_BELOW_OVERNIGHT_LOW")
        if breakout_confirmed:
            reasons.append("BREAKOUT_HAS_FOLLOW_THROUGH")
        elif high_breakout or low_breakout:
            reasons.append("BREAKOUT_STILL_NEEDS_FOLLOW_THROUGH")

        return OvernightSessionResult(
            valid=True,
            status=status,
            overnight_high=overnight_high,
            overnight_low=overnight_low,
            overnight_open=overnight_open,
            overnight_close=overnight_close,
            overnight_range=overnight_range,
            overnight_direction=overnight_direction,
            regular_open=regular_open,
            opening_location=opening_location,
            gap_points=round(gap_points, 8),
            gap_ratio=round(gap_ratio, 4),
            level_signal=level_signal,
            overnight_high_tested=high_tested,
            overnight_low_tested=low_tested,
            overnight_high_rejected=high_rejected,
            overnight_low_rejected=low_rejected,
            overnight_high_breakout=high_breakout,
            overnight_low_breakout=low_breakout,
            follow_through=follow_through,
            breakout_confirmed=breakout_confirmed,
            reversal_watch=reversal_watch,
            breakout_watch=breakout_watch,
            quality_score=round(score, 1),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _has_follow_through(candles, breakout_indices, level, direction):
        for index in breakout_indices:
            if index + 1 >= len(candles):
                continue

            next_bar = candles[index + 1]
            if direction == "UP" and float(next_bar.close) > level:
                return True
            if direction == "DOWN" and float(next_bar.close) < level:
                return True

        return False
