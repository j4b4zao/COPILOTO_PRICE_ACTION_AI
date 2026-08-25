"""
analysis/price_action/expanding_triangle_reversal_dynamics.py

Brooks Trading Price Action Reversals - Chapter 6:
Expanding Triangles.

Diagnostic-only layer. It detects expanding-triangle reversal structures and
never mutates Score/Risk/Decision or sends orders.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ExpandingTriangleReversalResult:
    valid: bool = False
    pattern: str = "NONE"
    direction: str = "NONE"
    state: str = "NO_EXPANDING_TRIANGLE"
    pivot_count: int = 0
    higher_highs: bool = False
    lower_lows: bool = False
    range_expanding: bool = False
    edge_rejection: bool = False
    failed_breakout: bool = False
    follow_through: bool = False
    volatility_expansion: float = 0.0
    quality_score: float = 0.0
    breakout_continuation_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ExpandingTriangleReversalDynamics:
    """Detect expanding triangles and confirmed reversals at their edges."""

    MIN_HISTORY = 14
    SWING_STRENGTH = 2
    LOOKBACK = 32

    def analyze(self, candles):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ExpandingTriangleReversalResult(
                reasons=("INSUFFICIENT_HISTORY",),
            )

        sample = closed[-self.LOOKBACK:]
        pivots = self._confirmed_pivots(sample)
        if len(pivots) < 5:
            return ExpandingTriangleReversalResult(
                pivot_count=len(pivots),
                reasons=("INSUFFICIENT_CONFIRMED_PIVOTS",),
            )

        highs = [p for p in pivots if p[1] == "HIGH"]
        lows = [p for p in pivots if p[1] == "LOW"]
        if len(highs) < 2 or len(lows) < 2:
            return ExpandingTriangleReversalResult(
                pivot_count=len(pivots),
                reasons=("NEED_AT_LEAST_TWO_HIGHS_AND_TWO_LOWS",),
            )

        h1, h2 = highs[-2], highs[-1]
        l1, l2 = lows[-2], lows[-1]
        higher_highs = h2[2] > h1[2]
        lower_lows = l2[2] < l1[2]

        old_width = max(h1[2] - l1[2], 1e-9)
        new_width = max(h2[2] - l2[2], 0.0)
        expansion = new_width / old_width
        range_expanding = expansion >= 1.10

        if not (higher_highs and lower_lows and range_expanding):
            return ExpandingTriangleReversalResult(
                pivot_count=len(pivots),
                higher_highs=higher_highs,
                lower_lows=lower_lows,
                range_expanding=range_expanding,
                volatility_expansion=round(expansion, 3),
                reasons=("NO_EXPANDING_TRIANGLE_SEQUENCE",),
            )

        direction, edge_rejection, failed_breakout = self._edge_reversal(
            closed, h2[2], l2[2]
        )
        follow_through = self._follow_through(closed, direction) if direction != "NONE" else False

        score = 45.0
        reasons = [
            "HIGHER_HIGH_SEQUENCE",
            "LOWER_LOW_SEQUENCE",
            "RANGE_EXPANSION_CONFIRMED",
        ]

        if expansion >= 1.25:
            score += 10.0
            reasons.append("STRONG_VOLATILITY_EXPANSION")
        if edge_rejection:
            score += 20.0
            reasons.append("EDGE_REJECTION")
        if failed_breakout:
            score += 15.0
            reasons.append("FAILED_BREAKOUT_AT_EDGE")
        if follow_through:
            score += 10.0
            reasons.append("OPPOSITE_FOLLOW_THROUGH")

        confirmed = edge_rejection and failed_breakout and follow_through
        if confirmed:
            state = "EXPANDING_TRIANGLE_REVERSAL_CONFIRMED"
            pattern = "EXPANDING_TRIANGLE_REVERSAL"
            continuation_risk = False
        elif edge_rejection and failed_breakout:
            state = "EXPANDING_TRIANGLE_WAIT_FOLLOW_THROUGH"
            pattern = "EXPANDING_TRIANGLE_REVERSAL_CANDIDATE"
            continuation_risk = True
        else:
            state = "EXPANDING_TRIANGLE_BREAKOUT_MODE"
            pattern = "EXPANDING_TRIANGLE"
            continuation_risk = True
            reasons.append("WAIT_EDGE_FAILURE_AND_CONFIRMATION")

        return ExpandingTriangleReversalResult(
            valid=True,
            pattern=pattern,
            direction=direction,
            state=state,
            pivot_count=len(pivots),
            higher_highs=True,
            lower_lows=True,
            range_expanding=True,
            edge_rejection=edge_rejection,
            failed_breakout=failed_breakout,
            follow_through=follow_through,
            volatility_expansion=round(expansion, 3),
            quality_score=round(min(score, 100.0), 1),
            breakout_continuation_risk=continuation_risk,
            reasons=tuple(reasons),
        )

    def _confirmed_pivots(self, candles):
        s = self.SWING_STRENGTH
        pivots = []
        for i in range(s, len(candles) - s):
            bar = candles[i]
            left = candles[i - s:i]
            right = candles[i + 1:i + s + 1]
            hi = float(bar.high)
            lo = float(bar.low)
            if all(hi > float(x.high) for x in left + right):
                pivots.append((i, "HIGH", hi))
            if all(lo < float(x.low) for x in left + right):
                pivots.append((i, "LOW", lo))
        return sorted(pivots, key=lambda x: x[0])

    @staticmethod
    def _edge_reversal(candles, upper_edge, lower_edge):
        if len(candles) < 3:
            return "NONE", False, False

        signal = candles[-2]
        high = float(signal.high)
        low = float(signal.low)
        open_ = float(signal.open)
        close = float(signal.close)

        # Upper-edge failure => SELL candidate.
        if high > upper_edge and close < upper_edge and close < open_:
            return "SELL", True, True

        # Lower-edge failure => BUY candidate.
        if low < lower_edge and close > lower_edge and close > open_:
            return "BUY", True, True

        return "NONE", False, False

    @staticmethod
    def _follow_through(candles, direction):
        if len(candles) < 2:
            return False
        signal = candles[-2]
        follow = candles[-1]
        if direction == "BUY":
            return (
                float(follow.close) > float(follow.open)
                and float(follow.close) > float(signal.high)
            )
        if direction == "SELL":
            return (
                float(follow.close) < float(follow.open)
                and float(follow.close) < float(signal.low)
            )
        return False
