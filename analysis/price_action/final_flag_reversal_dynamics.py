"""
analysis/price_action/final_flag_reversal_dynamics.py

Brooks Trading Price Action Reversals - Chapter 7: Final Flags.
Diagnostic-only layer. It does not mutate Score/Risk/Decision and does not send orders.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class FinalFlagReversalResult:
    valid: bool = False
    old_trend: str = "NONE"
    reversal_direction: str = "NONE"
    state: str = "NO_FINAL_FLAG"
    mature_trend: bool = False
    horizontal_flag: bool = False
    two_sided_trading: bool = False
    continuation_attempt: bool = False
    failed_continuation: bool = False
    reversal_signal: bool = False
    follow_through: bool = False
    reversal_confirmed: bool = False
    failed_reversal: bool = False
    quality_score: float = 0.0
    old_trend_continuation_risk: bool = True
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class FinalFlagReversalDynamics:
    """Detect a probable final flag and require failed continuation + reversal follow-through."""

    MIN_HISTORY = 18
    TREND_LOOKBACK = 18
    FLAG_BARS = 8

    def analyze(self, candles, old_trend=None):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return FinalFlagReversalResult(reasons=("INSUFFICIENT_HISTORY",))

        trend = str(old_trend or self._infer_old_trend(closed)).upper()
        if trend not in ("UP", "DOWN"):
            return FinalFlagReversalResult(reasons=("NO_CLEAR_OLD_TREND",))

        reversal_direction = "SELL" if trend == "UP" else "BUY"
        mature = self._mature_trend(closed, trend)
        flag = closed[-self.FLAG_BARS:]
        horizontal = self._horizontal_flag(flag)
        two_sided = self._two_sided(flag)

        if not (mature and horizontal and two_sided):
            return FinalFlagReversalResult(
                old_trend=trend,
                reversal_direction=reversal_direction,
                mature_trend=mature,
                horizontal_flag=horizontal,
                two_sided_trading=two_sided,
                reasons=("FINAL_FLAG_CRITERIA_INCOMPLETE",),
            )

        prior = closed[-self.FLAG_BARS-3:-self.FLAG_BARS]
        flag_high = max(float(c.high) for c in flag[:-2])
        flag_low = min(float(c.low) for c in flag[:-2])
        attempt = flag[-2]
        follow = flag[-1]

        if trend == "UP":
            continuation_attempt = float(attempt.high) > flag_high
            failed_continuation = continuation_attempt and float(attempt.close) < flag_high
            reversal_signal = float(attempt.close) < float(attempt.open)
            follow_through = float(follow.close) < float(attempt.low)
            failed_reversal = failed_continuation and float(follow.close) > flag_high
        else:
            continuation_attempt = float(attempt.low) < flag_low
            failed_continuation = continuation_attempt and float(attempt.close) > flag_low
            reversal_signal = float(attempt.close) > float(attempt.open)
            follow_through = float(follow.close) > float(attempt.high)
            failed_reversal = failed_continuation and float(follow.close) < flag_low

        confirmed = failed_continuation and reversal_signal and follow_through

        if confirmed:
            state = "FINAL_FLAG_REVERSAL_CONFIRMED"
        elif failed_reversal:
            state = "FINAL_FLAG_FAILED_REVERSAL"
        elif failed_continuation:
            state = "FINAL_FLAG_FAILED_CONTINUATION"
        elif continuation_attempt:
            state = "FINAL_FLAG_BREAKOUT_ATTEMPT"
        else:
            state = "FINAL_FLAG_CANDIDATE"

        score = 25.0
        score += 20.0 if mature else 0.0
        score += 15.0 if horizontal else 0.0
        score += 15.0 if two_sided else 0.0
        score += 10.0 if failed_continuation else 0.0
        score += 5.0 if reversal_signal else 0.0
        score += 10.0 if follow_through else 0.0
        score = min(score, 100.0)

        reasons = [f"OLD_TREND_{trend}", "MATURE_TREND", "HORIZONTAL_FLAG", "TWO_SIDED_TRADING"]
        if continuation_attempt:
            reasons.append("CONTINUATION_BREAKOUT_ATTEMPT")
        if failed_continuation:
            reasons.append("CONTINUATION_ATTEMPT_FAILED")
        if reversal_signal:
            reasons.append("OPPOSITE_SIGNAL_BAR")
        if follow_through:
            reasons.append("REVERSAL_FOLLOW_THROUGH")
        if failed_reversal:
            reasons.append("REVERSAL_FAILED_OLD_TREND_RESUMED")

        return FinalFlagReversalResult(
            valid=True,
            old_trend=trend,
            reversal_direction=reversal_direction,
            state=state,
            mature_trend=mature,
            horizontal_flag=horizontal,
            two_sided_trading=two_sided,
            continuation_attempt=continuation_attempt,
            failed_continuation=failed_continuation,
            reversal_signal=reversal_signal,
            follow_through=follow_through,
            reversal_confirmed=confirmed,
            failed_reversal=failed_reversal,
            quality_score=round(score, 1),
            old_trend_continuation_risk=not confirmed,
            reasons=tuple(reasons),
        )

    def _infer_old_trend(self, candles):
        sample = candles[-self.TREND_LOOKBACK:]
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        if delta >= atr * 3.0:
            return "UP"
        if delta <= -atr * 3.0:
            return "DOWN"
        return "NONE"

    def _mature_trend(self, candles, trend):
        sample = candles[-self.TREND_LOOKBACK:]
        directional = 0
        for c in sample:
            if trend == "UP" and float(c.close) > float(c.open):
                directional += 1
            elif trend == "DOWN" and float(c.close) < float(c.open):
                directional += 1
        return directional >= 9

    def _horizontal_flag(self, candles):
        atr = max(self._average_range(candles), 1e-9)
        total_range = max(float(c.high) for c in candles) - min(float(c.low) for c in candles)
        net = abs(float(candles[-1].close) - float(candles[0].close))
        return total_range <= atr * 3.6 and net <= atr * 1.4

    @staticmethod
    def _two_sided(candles):
        if len(candles) < 5:
            return False
        bull = sum(float(c.close) > float(c.open) for c in candles)
        bear = sum(float(c.close) < float(c.open) for c in candles)
        overlap = 0
        for a, b in zip(candles, candles[1:]):
            shared = min(float(a.high), float(b.high)) - max(float(a.low), float(b.low))
            if shared > 0:
                overlap += 1
        return bull >= 2 and bear >= 2 and overlap >= len(candles) // 2

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(c.high) - float(c.low), 0.0) for c in candles) / len(candles)
