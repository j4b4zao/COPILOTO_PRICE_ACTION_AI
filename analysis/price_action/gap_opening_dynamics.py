"""
analysis/price_action/gap_opening_dynamics.py

Brooks Reversals - Chapter 20:
Gap Openings: Reversals and Continuations.

Diagnostic-only layer. It does not alter Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class GapOpeningResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    previous_close: float = 0.0
    session_open: float = 0.0
    gap_size: float = 0.0
    gap_ratio: float = 0.0
    large_gap: bool = False
    early_two_sided: bool = False
    continuation: bool = False
    gap_fill: bool = False
    reversal: bool = False
    follow_through: bool = False
    trend_day_watch: bool = False
    trading_range_risk: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class GapOpeningDynamics:
    """Classify gap openings as continuation, fill/reversal, or unresolved range."""

    MIN_CLOSED_BARS = 4

    def analyze(self, *, previous_close, session_candles, reference_range):
        candles = list(session_candles or [])
        closed = candles[:-1] if candles else []

        previous_close = float(previous_close or 0.0)
        reference_range = float(reference_range or 0.0)

        if previous_close <= 0 or reference_range <= 0 or len(closed) < self.MIN_CLOSED_BARS:
            return GapOpeningResult(reasons=("INSUFFICIENT_OR_INVALID_CONTEXT",))

        session_open = float(closed[0].open)
        gap = session_open - previous_close
        gap_size = abs(gap)
        gap_ratio = gap_size / reference_range

        if gap_size == 0:
            return GapOpeningResult(
                valid=True,
                status="NO_GAP_OPENING",
                previous_close=previous_close,
                session_open=session_open,
                reasons=("SESSION_OPENED_AT_PREVIOUS_CLOSE",),
            )

        direction = "BUY" if gap > 0 else "SELL"
        large_gap = gap_ratio >= 0.50

        early = closed[: min(6, len(closed))]
        bulls = sum(float(b.close) > float(b.open) for b in early)
        bears = sum(float(b.close) < float(b.open) for b in early)
        two_sided = bulls >= 2 and bears >= 2

        if direction == "BUY":
            filled = any(float(b.low) <= previous_close for b in early)
            follow = len(early) >= 2 and sum(float(b.close) > session_open for b in early[1:]) >= 2
            reversed = filled and any(float(b.close) < session_open for b in early)
        else:
            filled = any(float(b.high) >= previous_close for b in early)
            follow = len(early) >= 2 and sum(float(b.close) < session_open for b in early[1:]) >= 2
            reversed = filled and any(float(b.close) > session_open for b in early)

        continuation = follow and not filled
        trend_day_watch = large_gap and continuation
        trading_range_risk = two_sided and not continuation and not reversed

        if reversed:
            status = "GAP_REVERSAL_CONFIRMED"
            score = 84.0
        elif continuation:
            status = "GAP_CONTINUATION_CONFIRMED"
            score = 88.0 if large_gap else 78.0
        elif filled:
            status = "GAP_FILL_IN_PROGRESS"
            score = 68.0
        elif two_sided:
            status = "GAP_OPENING_TRADING_RANGE"
            score = 52.0
        else:
            status = "GAP_OPENING_UNRESOLVED"
            score = 48.0

        reasons = [status, f"GAP_DIRECTION_{direction}"]
        if large_gap:
            reasons.append("LARGE_GAP_TREND_DAY_PROBABILITY_INCREASED")
        if two_sided:
            reasons.append("EARLY_TWO_SIDED_TRADING")
        if filled:
            reasons.append("PREVIOUS_CLOSE_TESTED_OR_FILLED")
        if follow:
            reasons.append("FOLLOW_THROUGH_PRESENT")

        return GapOpeningResult(
            valid=True,
            status=status,
            direction=direction,
            previous_close=previous_close,
            session_open=session_open,
            gap_size=gap_size,
            gap_ratio=round(gap_ratio, 4),
            large_gap=large_gap,
            early_two_sided=two_sided,
            continuation=continuation,
            gap_fill=filled,
            reversal=reversed,
            follow_through=follow,
            trend_day_watch=trend_day_watch,
            trading_range_risk=trading_range_risk,
            quality_score=score,
            reasons=tuple(reasons),
        )
