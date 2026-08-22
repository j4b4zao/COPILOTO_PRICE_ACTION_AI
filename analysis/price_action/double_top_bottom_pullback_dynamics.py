"""
analysis/price_action/double_top_bottom_pullback_dynamics.py

Brooks Trading Price Action Reversals - Chapter 8:
Double Top and Double Bottom Pullbacks.

Diagnostic-only layer. It distinguishes a simple double top/bottom from a
pullback/retest that occurs after a breakout and only confirms reversal when
there is failed continuation plus opposite follow-through.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class DoubleTopBottomPullbackResult:
    valid: bool = False
    pattern: str = "NONE"
    direction: str = "NONE"
    state: str = "NO_PATTERN"
    breakout_detected: bool = False
    retest_detected: bool = False
    near_equal_test: bool = False
    failed_continuation: bool = False
    opposite_signal: bool = False
    follow_through: bool = False
    reversal_confirmed: bool = False
    old_trend_continuation_risk: bool = False
    quality_score: float = 0.0
    reference_level: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class DoubleTopBottomPullbackDynamics:
    """Detect breakout -> pullback/retest -> failed continuation reversal."""

    MIN_HISTORY = 10
    LOOKBACK = 24
    EQUALITY_TOLERANCE = 0.25

    def analyze(self, candles, old_trend):
        old_trend = str(old_trend or "").upper()
        if old_trend not in ("UP", "DOWN"):
            return DoubleTopBottomPullbackResult(reasons=("INVALID_OLD_TREND",))

        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return DoubleTopBottomPullbackResult(reasons=("INSUFFICIENT_HISTORY",))

        sample = closed[-self.LOOKBACK:]
        atr = max(self._average_range(sample), 1e-9)

        if old_trend == "UP":
            pattern = "DOUBLE_TOP_PULLBACK"
            direction = "SELL"
            reference = max(float(c.high) for c in sample[:-4])
            breakout_idx = self._first_index(sample[-6:], lambda c: float(c.high) > reference)
            breakout_detected = breakout_idx is not None
            recent = sample[-4:]
            retest = any(abs(float(c.high) - reference) <= atr * self.EQUALITY_TOLERANCE for c in recent)
            failed = any(float(c.high) > reference and float(c.close) < reference for c in recent)
            opposite_signal = any(float(c.close) < float(c.open) for c in recent[-2:])
            follow = self._bear_follow_through(recent)
        else:
            pattern = "DOUBLE_BOTTOM_PULLBACK"
            direction = "BUY"
            reference = min(float(c.low) for c in sample[:-4])
            breakout_idx = self._first_index(sample[-6:], lambda c: float(c.low) < reference)
            breakout_detected = breakout_idx is not None
            recent = sample[-4:]
            retest = any(abs(float(c.low) - reference) <= atr * self.EQUALITY_TOLERANCE for c in recent)
            failed = any(float(c.low) < reference and float(c.close) > reference for c in recent)
            opposite_signal = any(float(c.close) > float(c.open) for c in recent[-2:])
            follow = self._bull_follow_through(recent)

        near_equal = retest
        confirmed = breakout_detected and retest and failed and opposite_signal and follow

        if confirmed:
            state = "DOUBLE_PULLBACK_REVERSAL_CONFIRMED"
        elif breakout_detected and retest and failed:
            state = "DOUBLE_PULLBACK_WAIT_FOLLOW_THROUGH"
        elif breakout_detected and retest:
            state = "DOUBLE_PULLBACK_RETEST"
        elif breakout_detected:
            state = "BREAKOUT_WAIT_RETEST"
        else:
            state = "NO_PATTERN"

        score = 0.0
        score += 20.0 if breakout_detected else 0.0
        score += 20.0 if retest else 0.0
        score += 20.0 if failed else 0.0
        score += 15.0 if opposite_signal else 0.0
        score += 25.0 if follow else 0.0

        reasons = [f"OLD_TREND_{old_trend}"]
        if breakout_detected:
            reasons.append("BREAKOUT_DETECTED")
        if retest:
            reasons.append("PULLBACK_RETEST_AT_REFERENCE")
        if failed:
            reasons.append("FAILED_CONTINUATION")
        if opposite_signal:
            reasons.append("OPPOSITE_SIGNAL")
        if follow:
            reasons.append("OPPOSITE_FOLLOW_THROUGH")
        if confirmed:
            reasons.append("DOUBLE_TOP_BOTTOM_PULLBACK_REVERSAL_CONFIRMED")

        return DoubleTopBottomPullbackResult(
            valid=breakout_detected or retest,
            pattern=pattern,
            direction=direction,
            state=state,
            breakout_detected=breakout_detected,
            retest_detected=retest,
            near_equal_test=near_equal,
            failed_continuation=failed,
            opposite_signal=opposite_signal,
            follow_through=follow,
            reversal_confirmed=confirmed,
            old_trend_continuation_risk=not confirmed,
            quality_score=round(score, 1),
            reference_level=round(reference, 6),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _first_index(candles, predicate):
        for i, candle in enumerate(candles):
            if predicate(candle):
                return i
        return None

    @staticmethod
    def _bull_follow_through(recent):
        if len(recent) < 2:
            return False
        a, b = recent[-2], recent[-1]
        return float(a.close) > float(a.open) and float(b.close) > float(a.high)

    @staticmethod
    def _bear_follow_through(recent):
        if len(recent) < 2:
            return False
        a, b = recent[-2], recent[-1]
        return float(a.close) < float(a.open) and float(b.close) < float(a.low)

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(c.high) - float(c.low), 0.0) for c in candles) / len(candles)
