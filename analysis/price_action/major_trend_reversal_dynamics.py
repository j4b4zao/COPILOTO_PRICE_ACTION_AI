"""
analysis/price_action/major_trend_reversal_dynamics.py

Brooks Reversals - Chapter 3: Major Trend Reversal.

Diagnostic-only layer. It models the structural sequence:
old trend -> meaningful structural break -> test of prior extreme ->
second attempt -> opposite follow-through.

It never sends orders and does not mutate Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class MajorTrendReversalResult:
    valid: bool = False
    old_trend: str = "NONE"
    reversal_direction: str = "NONE"
    state: str = "NO_MTR"
    structural_break: bool = False
    extreme_test: bool = False
    double_test: bool = False
    second_attempt: bool = False
    follow_through: bool = False
    old_trend_continuation_risk: bool = False
    structural_level: float = 0.0
    tested_extreme: float = 0.0
    quality_score: float = 0.0
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class MajorTrendReversalDynamics:
    """Detect a Brooks-style Major Trend Reversal sequence."""

    MIN_HISTORY = 10
    LOOKBACK = 24
    EXTREME_TOLERANCE_RATIO = 0.20

    def analyze(self, candles, old_trend, structural_break_index=None):
        old_trend = str(old_trend or "").upper()
        if old_trend not in ("UP", "DOWN"):
            return MajorTrendReversalResult(
                reason="INVALID_OLD_TREND",
                reasons=("INVALID_OLD_TREND",),
            )

        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return MajorTrendReversalResult(
                old_trend=old_trend,
                reversal_direction="SELL" if old_trend == "UP" else "BUY",
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        closed = closed[-self.LOOKBACK:]
        reversal_direction = "SELL" if old_trend == "UP" else "BUY"
        atr = self._average_range(closed)
        tolerance = max(atr * self.EXTREME_TOLERANCE_RATIO, 1e-9)

        if structural_break_index is None:
            structural_break_index = self._find_structural_break(closed, old_trend)

        reasons = []
        structural_break = structural_break_index is not None
        if structural_break:
            reasons.append("MEANINGFUL_STRUCTURAL_BREAK")

        if not structural_break:
            return MajorTrendReversalResult(
                valid=True,
                old_trend=old_trend,
                reversal_direction=reversal_direction,
                state="MTR_WATCH",
                old_trend_continuation_risk=True,
                quality_score=15.0,
                reason="WAIT_FOR_STRUCTURAL_BREAK",
                reasons=("WAIT_FOR_STRUCTURAL_BREAK",),
            )

        if not (2 <= structural_break_index < len(closed) - 2):
            return MajorTrendReversalResult(
                old_trend=old_trend,
                reversal_direction=reversal_direction,
                reason="INVALID_BREAK_INDEX",
                reasons=("INVALID_BREAK_INDEX",),
            )

        before = closed[:structural_break_index]
        after = closed[structural_break_index + 1:]
        structural_level = self._structural_level(before, old_trend)
        tested_extreme = self._old_extreme(before, old_trend)

        test_index = self._find_extreme_test(after, tested_extreme, old_trend, tolerance)
        extreme_test = test_index is not None
        double_test = False
        second_attempt = False
        follow_through = False

        if extreme_test:
            reasons.append("PRIOR_EXTREME_TESTED_AFTER_BREAK")
            test_bar = after[test_index]
            if old_trend == "UP":
                double_test = abs(float(test_bar.high) - tested_extreme) <= tolerance
            else:
                double_test = abs(float(test_bar.low) - tested_extreme) <= tolerance
            if double_test:
                reasons.append("DOUBLE_TEST_OR_NEAR_EQUAL_EXTREME")

            post_test = after[test_index + 1:]
            second_attempt = self._has_second_attempt(post_test, reversal_direction)
            if second_attempt:
                reasons.append("SECOND_REVERSAL_ATTEMPT")
                follow_through = self._has_follow_through(post_test, reversal_direction)
                if follow_through:
                    reasons.append("OPPOSITE_FOLLOW_THROUGH")

        if not extreme_test:
            state = "MTR_BREAK_ONLY"
        elif extreme_test and not second_attempt:
            state = "MTR_EXTREME_TEST"
        elif second_attempt and not follow_through:
            state = "MTR_SECOND_ATTEMPT_WAIT"
        else:
            state = "MTR_CONFIRMED"

        quality = 25.0
        if extreme_test:
            quality += 25.0
        if double_test:
            quality += 10.0
        if second_attempt:
            quality += 20.0
        if follow_through:
            quality += 20.0
        quality = min(100.0, quality)

        continuation_risk = not follow_through
        if continuation_risk:
            reasons.append("OLD_TREND_CONTINUATION_RISK")

        return MajorTrendReversalResult(
            valid=True,
            old_trend=old_trend,
            reversal_direction=reversal_direction,
            state=state,
            structural_break=True,
            extreme_test=extreme_test,
            double_test=double_test,
            second_attempt=second_attempt,
            follow_through=follow_through,
            old_trend_continuation_risk=continuation_risk,
            structural_level=round(structural_level, 6),
            tested_extreme=round(tested_extreme, 6),
            quality_score=round(quality, 1),
            reason=reasons[-1] if reasons else state,
            reasons=tuple(reasons or (state,)),
        )

    @staticmethod
    def _average_range(candles):
        values = [max(float(c.high) - float(c.low), 0.0) for c in candles]
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _structural_level(before, old_trend):
        recent = before[-5:]
        if old_trend == "UP":
            return min(float(c.low) for c in recent)
        return max(float(c.high) for c in recent)

    @staticmethod
    def _old_extreme(before, old_trend):
        if old_trend == "UP":
            return max(float(c.high) for c in before)
        return min(float(c.low) for c in before)

    def _find_structural_break(self, candles, old_trend):
        for i in range(4, len(candles) - 2):
            prior = candles[max(0, i - 5):i]
            bar = candles[i]
            if old_trend == "UP":
                support = min(float(c.low) for c in prior)
                if float(bar.close) < support:
                    return i
            else:
                resistance = max(float(c.high) for c in prior)
                if float(bar.close) > resistance:
                    return i
        return None

    @staticmethod
    def _find_extreme_test(after, extreme, old_trend, tolerance):
        for i, bar in enumerate(after):
            if old_trend == "UP":
                if float(bar.high) >= extreme - tolerance:
                    return i
            else:
                if float(bar.low) <= extreme + tolerance:
                    return i
        return None

    @staticmethod
    def _has_second_attempt(candles, direction):
        if len(candles) < 2:
            return False
        directional = 0
        for bar in candles[:4]:
            o = float(bar.open)
            c = float(bar.close)
            if direction == "BUY" and c > o:
                directional += 1
            elif direction == "SELL" and c < o:
                directional += 1
        return directional >= 2

    @staticmethod
    def _has_follow_through(candles, direction):
        if len(candles) < 2:
            return False
        sample = candles[:3]
        closes = [float(c.close) for c in sample]
        if direction == "BUY":
            return closes[-1] > closes[0] and sum(float(c.close) > float(c.open) for c in sample) >= 2
        return closes[-1] < closes[0] and sum(float(c.close) < float(c.open) for c in sample) >= 2
