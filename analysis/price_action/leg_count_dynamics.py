"""
analysis/price_action/leg_count_dynamics.py

Brooks Trading Ranges - Chapter 16:
Counting legs in trends and trading ranges.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class LegCountResult:
    valid: bool = False
    context: str = "NONE"
    direction: str = "NONE"
    leg_count: int = 0
    leg_state: str = "NO_LEG"
    two_leg_complete: bool = False
    third_attempt: bool = False
    fourth_plus_attempt: bool = False
    last_leg_size: float = 0.0
    previous_leg_size: float = 0.0
    leg_size_ratio: float = 0.0
    compressing: bool = False
    expanding: bool = False
    continuation_bias: bool = False
    exhaustion_risk: bool = False
    trading_range_risk: bool = False
    pivot_count: int = 0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class LegCountDynamics:
    """Count directional legs using confirmed swing pivots."""

    MIN_HISTORY = 12
    SWING_STRENGTH = 2
    MIN_LEG_ATR = 0.60

    def analyze(self, candles):
        # The last candle is assumed to be current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return LegCountResult(reasons=("INSUFFICIENT_HISTORY",))

        atr = max(self._average_range(closed[-12:]), 1e-9)
        pivots = self._confirmed_pivots(closed)

        if len(pivots) < 3:
            return LegCountResult(
                pivot_count=len(pivots),
                reasons=("INSUFFICIENT_CONFIRMED_PIVOTS",),
            )

        pivots = self._compress_same_type_pivots(pivots)
        legs = self._build_legs(pivots, atr)

        if not legs:
            return LegCountResult(
                pivot_count=len(pivots),
                reasons=("NO_SIGNIFICANT_LEGS",),
            )

        context = self._classify_context(closed, legs)
        direction = self._dominant_direction(legs)
        counted = self._count_directional_attempts(legs, direction)

        last_leg_size = abs(legs[-1][3] - legs[-1][2])
        previous_leg_size = (
            abs(legs[-2][3] - legs[-2][2])
            if len(legs) >= 2
            else 0.0
        )
        leg_size_ratio = (
            last_leg_size / previous_leg_size
            if previous_leg_size > 0
            else 0.0
        )

        compressing = previous_leg_size > 0 and leg_size_ratio <= 0.75
        expanding = previous_leg_size > 0 and leg_size_ratio >= 1.25
        two_leg_complete = counted >= 2
        third_attempt = counted == 3
        fourth_plus_attempt = counted >= 4

        continuation_bias = counted in (1, 2) and not compressing
        exhaustion_risk = counted >= 3 or (counted >= 2 and compressing)
        trading_range_risk = context == "TRADING_RANGE" or exhaustion_risk

        reasons = [
            f"CONTEXT_{context}",
            f"DIRECTION_{direction}",
            f"LEG_COUNT_{counted}",
        ]
        if two_leg_complete:
            reasons.append("TWO_LEG_COMPLETE")
        if third_attempt:
            reasons.append("THIRD_ATTEMPT")
        if fourth_plus_attempt:
            reasons.append("FOURTH_PLUS_ATTEMPT")
        if compressing:
            reasons.append("LEG_COMPRESSION")
        if expanding:
            reasons.append("LEG_EXPANSION")
        if exhaustion_risk:
            reasons.append("EXHAUSTION_RISK")

        return LegCountResult(
            valid=True,
            context=context,
            direction=direction,
            leg_count=counted,
            leg_state=(
                "LEG_4_PLUS"
                if counted >= 4
                else f"LEG_{max(counted, 1)}"
            ),
            two_leg_complete=two_leg_complete,
            third_attempt=third_attempt,
            fourth_plus_attempt=fourth_plus_attempt,
            last_leg_size=round(last_leg_size, 6),
            previous_leg_size=round(previous_leg_size, 6),
            leg_size_ratio=round(leg_size_ratio, 3),
            compressing=compressing,
            expanding=expanding,
            continuation_bias=continuation_bias,
            exhaustion_risk=exhaustion_risk,
            trading_range_risk=trading_range_risk,
            pivot_count=len(pivots),
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

            is_high = all(high > float(x.high) for x in left + right)
            is_low = all(low < float(x.low) for x in left + right)

            if is_high:
                pivots.append((i, "HIGH", high))
            if is_low:
                pivots.append((i, "LOW", low))

        pivots.sort(key=lambda x: x[0])
        return pivots

    @staticmethod
    def _compress_same_type_pivots(pivots):
        if not pivots:
            return []

        result = [pivots[0]]
        for pivot in pivots[1:]:
            prev = result[-1]
            if pivot[1] != prev[1]:
                result.append(pivot)
                continue

            if pivot[1] == "HIGH" and pivot[2] >= prev[2]:
                result[-1] = pivot
            elif pivot[1] == "LOW" and pivot[2] <= prev[2]:
                result[-1] = pivot

        return result

    def _build_legs(self, pivots, atr):
        legs = []
        for a, b in zip(pivots, pivots[1:]):
            if a[1] == b[1]:
                continue

            direction = "UP" if a[1] == "LOW" else "DOWN"
            size = abs(b[2] - a[2])
            if size < atr * self.MIN_LEG_ATR:
                continue

            legs.append((direction, a[0], a[2], b[2]))
        return legs

    def _classify_context(self, candles, legs):
        sample = candles[-10:]
        if len(sample) < 8:
            return "TRANSITION"

        overlap = 0
        for a, b in zip(sample, sample[1:]):
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlap += 1

        bulls = sum(float(x.close) > float(x.open) for x in sample)
        bears = sum(float(x.close) < float(x.open) for x in sample)

        if overlap >= 6 and bulls >= 3 and bears >= 3:
            return "TRADING_RANGE"

        dominant = self._dominant_direction(legs)
        if dominant in ("UP", "DOWN"):
            return "TREND"
        return "TRANSITION"

    @staticmethod
    def _dominant_direction(legs):
        up = sum(abs(end - start) for d, _, start, end in legs if d == "UP")
        down = sum(abs(end - start) for d, _, start, end in legs if d == "DOWN")
        if up > down * 1.10:
            return "UP"
        if down > up * 1.10:
            return "DOWN"
        return legs[-1][0]

    @staticmethod
    def _count_directional_attempts(legs, direction):
        count = 0
        for leg in legs:
            if leg[0] == direction:
                count += 1
        return count

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
