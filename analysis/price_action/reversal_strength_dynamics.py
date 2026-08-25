"""
analysis/price_action/reversal_strength_dynamics.py

Brooks Reversals - Chapter 2:
Signs of Strength in a Reversal.

Diagnostic-only layer. Measures evidence that a reversal is gaining strength
without mutating Score/Risk/Decision or sending orders.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ReversalStrengthResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_REVERSAL_STRENGTH"
    score: float = 0.0
    directional_bars: int = 0
    consecutive_directional_bars: int = 0
    strong_bars: int = 0
    strong_close_bars: int = 0
    low_overlap: bool = False
    follow_through: bool = False
    micro_gap: bool = False
    persistence: bool = False
    structural_break: bool = False
    strong_reversal: bool = False
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ReversalStrengthDynamics:
    """Measure cumulative strength in an attempted reversal."""

    MIN_HISTORY = 7
    WINDOW = 6
    STRONG_BODY_RATIO = 0.60
    STRONG_CLOSE_POSITION = 0.70
    LOW_OVERLAP_RATIO = 0.35

    def analyze(self, candles, direction, structural_break=False):
        direction = str(direction or "").upper()
        if direction not in ("BUY", "SELL"):
            return ReversalStrengthResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ReversalStrengthResult(
                direction=direction,
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        window = closed[-self.WINDOW:]
        reasons = []

        directional = [self._directional(c, direction) for c in window]
        directional_bars = sum(directional)
        consecutive = self._max_consecutive(directional)

        strong = [self._strong_bar(c, direction) for c in window]
        strong_bars = sum(strong)

        strong_close = [self._strong_close(c, direction) for c in window]
        strong_close_bars = sum(strong_close)

        low_overlap = self._low_overlap(window)
        follow_through = self._follow_through(window, direction)
        micro_gap = self._micro_gap(window, direction)
        persistence = directional_bars >= 4 or consecutive >= 3

        score = 0.0
        score += min(directional_bars * 7.5, 30.0)
        score += min(strong_bars * 10.0, 20.0)
        score += min(strong_close_bars * 5.0, 10.0)
        if consecutive >= 3:
            score += 10.0
            reasons.append("THREE_OR_MORE_CONSECUTIVE_DIRECTIONAL_BARS")
        if low_overlap:
            score += 10.0
            reasons.append("LOW_BAR_OVERLAP")
        if follow_through:
            score += 10.0
            reasons.append("FOLLOW_THROUGH_PRESENT")
        if micro_gap:
            score += 5.0
            reasons.append("MICRO_GAP_URGENCY")
        if structural_break:
            score += 15.0
            reasons.append("STRUCTURAL_BREAK_CONFIRMED")

        score = min(score, 100.0)

        if directional_bars:
            reasons.append(f"DIRECTIONAL_BARS_{directional_bars}")
        if strong_bars:
            reasons.append(f"STRONG_BARS_{strong_bars}")
        if strong_close_bars:
            reasons.append(f"STRONG_CLOSE_BARS_{strong_close_bars}")
        if persistence:
            reasons.append("REVERSAL_PRESSURE_PERSISTENT")

        strong_reversal = score >= 70.0 and follow_through and persistence

        if strong_reversal:
            state = "REVERSAL_STRENGTH_CONFIRMED"
            reasons.append("CUMULATIVE_REVERSAL_STRENGTH_CONFIRMED")
        elif score >= 50.0:
            state = "REVERSAL_STRENGTH_BUILDING"
        elif score >= 25.0:
            state = "REVERSAL_STRENGTH_WEAK"
        else:
            state = "NO_REVERSAL_STRENGTH"

        if not reasons:
            reasons.append("NO_MEANINGFUL_REVERSAL_STRENGTH")

        return ReversalStrengthResult(
            valid=True,
            direction=direction,
            state=state,
            score=round(score, 1),
            directional_bars=directional_bars,
            consecutive_directional_bars=consecutive,
            strong_bars=strong_bars,
            strong_close_bars=strong_close_bars,
            low_overlap=low_overlap,
            follow_through=follow_through,
            micro_gap=micro_gap,
            persistence=persistence,
            structural_break=bool(structural_break),
            strong_reversal=strong_reversal,
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    @classmethod
    def _directional(cls, candle, direction):
        open_ = float(candle.open)
        close = float(candle.close)
        return close > open_ if direction == "BUY" else close < open_

    @classmethod
    def _strong_bar(cls, candle, direction):
        high = float(candle.high)
        low = float(candle.low)
        open_ = float(candle.open)
        close = float(candle.close)
        rng = max(high - low, 1e-9)
        body_ratio = abs(close - open_) / rng
        return cls._directional(candle, direction) and body_ratio >= cls.STRONG_BODY_RATIO

    @classmethod
    def _strong_close(cls, candle, direction):
        high = float(candle.high)
        low = float(candle.low)
        close = float(candle.close)
        rng = max(high - low, 1e-9)
        if direction == "BUY":
            pos = (close - low) / rng
        else:
            pos = (high - close) / rng
        return cls._directional(candle, direction) and pos >= cls.STRONG_CLOSE_POSITION

    @classmethod
    def _low_overlap(cls, bars):
        if len(bars) < 2:
            return False
        ratios = []
        for prev, cur in zip(bars, bars[1:]):
            overlap = max(0.0, min(float(prev.high), float(cur.high)) - max(float(prev.low), float(cur.low)))
            denom = max(min(float(prev.high) - float(prev.low), float(cur.high) - float(cur.low)), 1e-9)
            ratios.append(overlap / denom)
        return sum(ratios) / len(ratios) <= cls.LOW_OVERLAP_RATIO

    @classmethod
    def _follow_through(cls, bars, direction):
        if len(bars) < 2:
            return False
        last_two = bars[-2:]
        return all(cls._directional(c, direction) for c in last_two) and any(
            cls._strong_bar(c, direction) for c in last_two
        )

    @staticmethod
    def _micro_gap(bars, direction):
        if len(bars) < 3:
            return False
        a, _, c = bars[-3], bars[-2], bars[-1]
        if direction == "BUY":
            return float(c.low) >= float(a.high)
        return float(c.high) <= float(a.low)

    @staticmethod
    def _max_consecutive(flags):
        best = current = 0
        for flag in flags:
            if flag:
                current += 1
                best = max(best, current)
            else:
                current = 0
        return best
