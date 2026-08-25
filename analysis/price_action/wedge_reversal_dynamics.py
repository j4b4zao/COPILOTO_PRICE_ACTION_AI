"""
analysis/price_action/wedge_reversal_dynamics.py

Brooks Trading Price Action Reversals - Chapter 5:
Wedges and other three-push reversal patterns.

Diagnostic-only layer. It detects exhaustion through three pushes in the
old-trend direction and requires structural/price-action confirmation before
calling the pattern a reversal. It does not mutate Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class WedgeReversalResult:
    valid: bool = False
    old_trend: str = "NONE"
    reversal_direction: str = "NONE"
    state: str = "NO_WEDGE_REVERSAL"
    push_count: int = 0
    push_sizes: tuple[float, ...] = ()
    shrinking_pushes: bool = False
    momentum_loss: bool = False
    structural_break: bool = False
    opposite_signal: bool = False
    follow_through: bool = False
    reversal_confirmed: bool = False
    old_trend_continuation_risk: bool = True
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class WedgeReversalDynamics:
    """Detect three-push exhaustion that can develop into a real reversal."""

    MIN_HISTORY = 16
    SWING_STRENGTH = 2
    LOOKBACK = 34

    def analyze(self, candles, old_trend=None, structural_break=False):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return WedgeReversalResult(reasons=("INSUFFICIENT_HISTORY",))

        trend = str(old_trend or self._infer_trend(closed)).upper()
        if trend not in ("UP", "DOWN"):
            return WedgeReversalResult(reasons=("NO_CLEAR_OLD_TREND",))

        pivots = self._confirmed_pivots(closed[-self.LOOKBACK:])
        pushes = self._trend_pushes(pivots, trend)
        if len(pushes) < 3:
            return WedgeReversalResult(
                old_trend=trend,
                reversal_direction="SELL" if trend == "UP" else "BUY",
                push_count=len(pushes),
                reasons=("LESS_THAN_THREE_TREND_PUSHES",),
            )

        pushes = pushes[-3:]
        sizes = tuple(round(abs(end - start), 6) for start, end in pushes)
        shrinking = sizes[1] <= sizes[0] * 0.92 and sizes[2] <= sizes[1] * 0.92
        momentum_loss = shrinking or self._reduced_extreme_progress(pushes)

        opposite_signal, follow = self._opposite_response(closed, trend)
        internal_break = bool(structural_break) or self._local_structural_break(closed, trend)

        score = 25.0
        reasons = [f"OLD_TREND_{trend}", "THREE_TREND_PUSHES"]
        if momentum_loss:
            score += 25.0
            reasons.append("MOMENTUM_LOSS")
        if shrinking:
            score += 10.0
            reasons.append("SHRINKING_PUSHES")
        if internal_break:
            score += 15.0
            reasons.append("STRUCTURAL_BREAK")
        if opposite_signal:
            score += 10.0
            reasons.append("OPPOSITE_SIGNAL")
        if follow:
            score += 15.0
            reasons.append("OPPOSITE_FOLLOW_THROUGH")

        confirmed = momentum_loss and internal_break and opposite_signal and follow
        reversal_direction = "SELL" if trend == "UP" else "BUY"

        if confirmed:
            state = "WEDGE_REVERSAL_CONFIRMED"
            reasons.append("REVERSAL_SEQUENCE_CONFIRMED")
        elif internal_break and opposite_signal:
            state = "WEDGE_REVERSAL_WAIT_FOLLOW_THROUGH"
            reasons.append("WAIT_FOLLOW_THROUGH")
        elif momentum_loss:
            state = "THREE_PUSH_EXHAUSTION_WATCH"
            reasons.append("WAIT_STRUCTURAL_BREAK")
        else:
            state = "THREE_PUSH_PATTERN_ONLY"
            reasons.append("THREE_PUSHES_WITHOUT_ENOUGH_EXHAUSTION")

        return WedgeReversalResult(
            valid=True,
            old_trend=trend,
            reversal_direction=reversal_direction,
            state=state,
            push_count=3,
            push_sizes=sizes,
            shrinking_pushes=shrinking,
            momentum_loss=momentum_loss,
            structural_break=internal_break,
            opposite_signal=opposite_signal,
            follow_through=follow,
            reversal_confirmed=confirmed,
            old_trend_continuation_risk=not confirmed,
            quality_score=round(min(score, 100.0), 1),
            reasons=tuple(reasons),
        )

    def _infer_trend(self, candles):
        sample = candles[-14:]
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        if delta >= atr * 2.0:
            return "UP"
        if delta <= -atr * 2.0:
            return "DOWN"
        return "NONE"

    def _confirmed_pivots(self, candles):
        s = self.SWING_STRENGTH
        pivots = []
        for i in range(s, len(candles) - s):
            bar = candles[i]
            left = candles[i - s:i]
            right = candles[i + 1:i + s + 1]
            high = float(bar.high)
            low = float(bar.low)
            if all(high > float(x.high) for x in left + right):
                pivots.append((i, "HIGH", high))
            if all(low < float(x.low) for x in left + right):
                pivots.append((i, "LOW", low))
        return sorted(pivots, key=lambda item: item[0])

    @staticmethod
    def _trend_pushes(pivots, trend):
        pushes = []
        target = "HIGH" if trend == "UP" else "LOW"
        start_type = "LOW" if trend == "UP" else "HIGH"
        for start, end in zip(pivots, pivots[1:]):
            if start[1] == start_type and end[1] == target:
                pushes.append((start[2], end[2]))
        return pushes

    @staticmethod
    def _reduced_extreme_progress(pushes):
        p1 = abs(pushes[1][1] - pushes[0][1])
        p2 = abs(pushes[2][1] - pushes[1][1])
        return p1 > 0 and p2 <= p1 * 0.90

    def _local_structural_break(self, candles, trend):
        if len(candles) < 8:
            return False
        prior = candles[-8:-2]
        recent = candles[-2:]
        if trend == "UP":
            reference = min(float(c.low) for c in prior[-4:])
            return any(float(c.close) < reference for c in recent)
        reference = max(float(c.high) for c in prior[-4:])
        return any(float(c.close) > reference for c in recent)

    def _opposite_response(self, candles, trend):
        if len(candles) < 3:
            return False, False
        signal = candles[-2]
        follow = candles[-1]
        atr = max(self._average_range(candles[-10:]), 1e-9)
        if trend == "UP":
            body = float(signal.open) - float(signal.close)
            opposite = body >= atr * 0.45 and float(signal.close) < float(signal.open)
            follow_through = opposite and float(follow.close) < float(signal.low)
        else:
            body = float(signal.close) - float(signal.open)
            opposite = body >= atr * 0.45 and float(signal.close) > float(signal.open)
            follow_through = opposite and float(follow.close) > float(signal.high)
        return opposite, follow_through

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(c.high) - float(c.low), 0.0) for c in candles) / len(candles)
