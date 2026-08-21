"""
analysis/price_action/triangle_dynamics.py

Brooks Trading Ranges - Chapter 23:
Triangles and breakout mode.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TriangleResult:
    valid: bool = False
    state: str = "NO_TRIANGLE"
    breakout_mode: bool = False
    direction: str = "NONE"
    compression_score: float = 0.0
    upper_slope: float = 0.0
    lower_slope: float = 0.0
    apex_distance_bars: float = 0.0
    breakout_attempt: bool = False
    breakout_confirmed: bool = False
    follow_through: bool = False
    failed_breakout_risk: bool = False
    measured_move_target: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TriangleDynamics:
    MIN_HISTORY = 14
    SWING_STRENGTH = 1
    LOOKBACK = 24

    def analyze(self, candles):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TriangleResult(reasons=("INSUFFICIENT_HISTORY",))

        sample = closed[-self.LOOKBACK:]
        pivots = self._confirmed_pivots(sample)
        highs = [p for p in pivots if p[1] == "HIGH"]
        lows = [p for p in pivots if p[1] == "LOW"]

        if len(highs) < 2 or len(lows) < 2:
            return TriangleResult(reasons=("INSUFFICIENT_TRIANGLE_PIVOTS",))

        h1, h2 = highs[-2], highs[-1]
        l1, l2 = lows[-2], lows[-1]
        upper_slope = self._slope(h1, h2)
        lower_slope = self._slope(l1, l2)

        if not (upper_slope < 0 and lower_slope > 0):
            return TriangleResult(
                reasons=("NO_CONVERGING_BOUNDARIES",),
                upper_slope=round(upper_slope, 6),
                lower_slope=round(lower_slope, 6),
            )

        first_width = max(h1[2] - l1[2], 1e-9)
        last_width = max(h2[2] - l2[2], 0.0)
        compression = max(0.0, min(1.0, 1.0 - last_width / first_width))

        current_index = len(sample) - 1
        upper_now = self._line_value(h1, h2, current_index)
        lower_now = self._line_value(l1, l2, current_index)
        apex = self._apex_index(h1, h2, l1, l2)
        apex_distance = max(0.0, apex - current_index) if apex is not None else 0.0

        breakout_attempt, direction, signal_idx = self._find_breakout_attempt(sample, h1, h2, l1, l2)
        follow_through = False
        breakout_confirmed = False
        failed_breakout_risk = False
        measured_target = 0.0

        if breakout_attempt and signal_idx is not None:
            signal = sample[signal_idx]
            if signal_idx + 1 < len(sample):
                follow = sample[signal_idx + 1]
                if direction == "BUY":
                    boundary = self._line_value(h1, h2, signal_idx + 1)
                    follow_through = float(follow.close) > float(signal.close) and float(follow.close) > boundary
                    failed_breakout_risk = float(follow.close) <= boundary
                else:
                    boundary = self._line_value(l1, l2, signal_idx + 1)
                    follow_through = float(follow.close) < float(signal.close) and float(follow.close) < boundary
                    failed_breakout_risk = float(follow.close) >= boundary
                breakout_confirmed = follow_through

            if breakout_confirmed:
                height = max(upper_now - lower_now, 0.0)
                measured_target = float(signal.close) + height if direction == "BUY" else float(signal.close) - height

        state = "TRIANGLE_BREAKOUT_MODE"
        if breakout_attempt and not breakout_confirmed:
            state = "TRIANGLE_BREAKOUT_ATTEMPT"
        if breakout_confirmed:
            state = "TRIANGLE_BREAKOUT_CONFIRMED"

        reasons = ["DESCENDING_HIGHS", "ASCENDING_LOWS", "CONVERGING_RANGE", "BREAKOUT_MODE"]
        if compression >= 0.25:
            reasons.append("MEANINGFUL_COMPRESSION")
        if breakout_attempt:
            reasons.append(f"BREAKOUT_ATTEMPT_{direction}")
        if follow_through:
            reasons.append("FOLLOW_THROUGH")
        if failed_breakout_risk:
            reasons.append("FAILED_BREAKOUT_RISK")

        return TriangleResult(
            valid=True,
            state=state,
            breakout_mode=not breakout_confirmed,
            direction=direction if breakout_attempt else "NONE",
            compression_score=round(compression * 100.0, 1),
            upper_slope=round(upper_slope, 6),
            lower_slope=round(lower_slope, 6),
            apex_distance_bars=round(apex_distance, 2),
            breakout_attempt=breakout_attempt,
            breakout_confirmed=breakout_confirmed,
            follow_through=follow_through,
            failed_breakout_risk=failed_breakout_risk,
            measured_move_target=round(measured_target, 6),
            reasons=tuple(reasons),
        )

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
        pivots.sort(key=lambda x: x[0])
        return pivots

    @staticmethod
    def _slope(a, b):
        dx = b[0] - a[0]
        return 0.0 if dx == 0 else (b[2] - a[2]) / dx

    @classmethod
    def _line_value(cls, a, b, index):
        return a[2] + cls._slope(a, b) * (index - a[0])

    @classmethod
    def _apex_index(cls, h1, h2, l1, l2):
        sh = cls._slope(h1, h2)
        sl = cls._slope(l1, l2)
        denom = sh - sl
        if abs(denom) < 1e-9:
            return None
        bh = h1[2] - sh * h1[0]
        bl = l1[2] - sl * l1[0]
        return (bl - bh) / denom

    def _find_breakout_attempt(self, candles, h1, h2, l1, l2):
        start = max(h2[0], l2[0]) + 1
        for i in range(start, len(candles)):
            close = float(candles[i].close)
            upper = self._line_value(h1, h2, i)
            lower = self._line_value(l1, l2, i)
            if close > upper:
                return True, "BUY", i
            if close < lower:
                return True, "SELL", i
        return False, "NONE", None
