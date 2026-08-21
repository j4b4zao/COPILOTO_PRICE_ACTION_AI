"""
analysis/price_action/wedge_pullback_dynamics.py

Brooks Trading Ranges - Chapter 18:
Wedge and other three-push pullbacks.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class WedgePullbackResult:
    valid: bool = False
    trend_direction: str = "NONE"
    wedge_direction: str = "NONE"
    setup_direction: str = "NONE"
    pattern: str = "NONE"
    push_count: int = 0
    push_sizes: tuple[float, ...] = ()
    shrinking_pushes: bool = False
    expanding_pushes: bool = False
    tight_channel: bool = False
    with_trend_pullback: bool = False
    countertrend_reversal: bool = False
    breakout_confirmed: bool = False
    breakout_strength: float = 0.0
    continuation_bias: bool = False
    reversal_watch: bool = False
    exhaustion_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class WedgePullbackDynamics:
    """Detect three-push wedge pullbacks and distinguish continuation from reversal."""

    MIN_HISTORY = 14
    SWING_STRENGTH = 2
    LOOKBACK = 28

    def analyze(self, candles):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return WedgePullbackResult(reasons=("INSUFFICIENT_HISTORY",))

        trend = self._infer_trend(closed)
        if trend == "NONE":
            return WedgePullbackResult(reasons=("NO_CLEAR_TREND",))

        pivots = self._confirmed_pivots(closed[-self.LOOKBACK:])
        if len(pivots) < 5:
            return WedgePullbackResult(
                trend_direction=trend,
                reasons=("INSUFFICIENT_CONFIRMED_PIVOTS",),
            )

        pushes = self._extract_countertrend_pushes(pivots, trend)
        if len(pushes) < 3:
            return WedgePullbackResult(
                trend_direction=trend,
                push_count=len(pushes),
                reasons=("LESS_THAN_THREE_PUSHES",),
            )

        pushes = pushes[-3:]
        sizes = tuple(round(abs(b - a), 6) for a, b in pushes)
        wedge_direction = "DOWN" if trend == "UP" else "UP"
        setup_direction = "BUY" if trend == "UP" else "SELL"

        shrinking = sizes[1] <= sizes[0] * 0.90 and sizes[2] <= sizes[1] * 0.90
        expanding = sizes[1] >= sizes[0] * 1.10 and sizes[2] >= sizes[1] * 1.10
        tight = self._tight_channel(closed[-12:])

        breakout_confirmed, breakout_strength = self._breakout_status(
            closed, trend, wedge_direction
        )

        with_trend = True
        countertrend_reversal = False
        continuation_bias = breakout_confirmed and not tight
        reversal_watch = shrinking or expanding
        exhaustion_risk = shrinking or len(pushes) >= 3

        if tight and not breakout_confirmed:
            pattern = "THREE_PUSH_TIGHT_CHANNEL"
            continuation_bias = False
        elif breakout_confirmed:
            pattern = "WEDGE_PULLBACK_CONFIRMED"
        else:
            pattern = "WEDGE_PULLBACK_WAIT"

        reasons = [
            f"TREND_{trend}",
            "THREE_PUSH_PATTERN",
            f"WEDGE_{wedge_direction}",
        ]
        if shrinking:
            reasons.append("SHRINKING_STAIRS")
        if expanding:
            reasons.append("EXPANDING_PUSHES")
        if tight:
            reasons.append("TIGHT_CHANNEL_CAUTION")
        if breakout_confirmed:
            reasons.append("WITH_TREND_BREAKOUT_CONFIRMED")
        else:
            reasons.append("WAIT_BREAKOUT_CONFIRMATION")

        return WedgePullbackResult(
            valid=True,
            trend_direction=trend,
            wedge_direction=wedge_direction,
            setup_direction=setup_direction,
            pattern=pattern,
            push_count=3,
            push_sizes=sizes,
            shrinking_pushes=shrinking,
            expanding_pushes=expanding,
            tight_channel=tight,
            with_trend_pullback=with_trend,
            countertrend_reversal=countertrend_reversal,
            breakout_confirmed=breakout_confirmed,
            breakout_strength=round(breakout_strength, 1),
            continuation_bias=continuation_bias,
            reversal_watch=reversal_watch,
            exhaustion_risk=exhaustion_risk,
            reasons=tuple(reasons),
        )

    def _infer_trend(self, candles):
        sample = candles[-12:]
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        if delta >= atr * 1.8:
            return "UP"
        if delta <= -atr * 1.8:
            return "DOWN"
        return "NONE"

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
    def _extract_countertrend_pushes(pivots, trend):
        pushes = []
        target = "LOW" if trend == "UP" else "HIGH"
        opposite = "HIGH" if trend == "UP" else "LOW"
        for a, b in zip(pivots, pivots[1:]):
            if a[1] == opposite and b[1] == target:
                pushes.append((a[2], b[2]))
        return pushes

    def _tight_channel(self, candles):
        if len(candles) < 6:
            return False
        overlap = 0
        for a, b in zip(candles, candles[1:]):
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlap += 1
        return overlap <= 3

    def _breakout_status(self, candles, trend, wedge_direction):
        if len(candles) < 4:
            return False, 0.0
        signal = candles[-2]
        follow = candles[-1]
        atr = max(self._average_range(candles[-10:]), 1e-9)

        if trend == "UP":
            confirmed = (
                float(signal.close) > float(signal.open)
                and float(follow.close) > float(signal.high)
            )
            body = max(float(signal.close) - float(signal.open), 0.0)
        else:
            confirmed = (
                float(signal.close) < float(signal.open)
                and float(follow.close) < float(signal.low)
            )
            body = max(float(signal.open) - float(signal.close), 0.0)

        strength = min(100.0, (body / atr) * 60.0 + (40.0 if confirmed else 0.0))
        return confirmed, strength

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(x.high) - float(x.low), 0.0) for x in candles) / len(candles)
