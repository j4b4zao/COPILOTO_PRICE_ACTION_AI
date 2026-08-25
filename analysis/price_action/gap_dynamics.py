"""
analysis/price_action/gap_dynamics.py

Brooks Trading Ranges - Chapter 6: Gaps.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class GapDynamicsResult:
    valid: bool = False
    direction: str = "NONE"
    gap_type: str = "NONE"
    gap_index: int = -1
    gap_low: float = 0.0
    gap_high: float = 0.0
    gap_size: float = 0.0
    gap_mid: float = 0.0
    held_open: bool = False
    filled: bool = False
    follow_through_count: int = 0
    trend_age: int = 0
    measuring_target: float = 0.0
    breakout_strength: bool = False
    exhaustion_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class GapDynamics:
    """Classify price gaps using only closed candles."""

    MIN_HISTORY = 8
    TREND_WINDOW = 8
    FOLLOW_THROUGH_BARS = 3

    def analyze(self, candles):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return GapDynamicsResult(reasons=("INSUFFICIENT_HISTORY",))

        found = self._find_latest_gap(closed)
        if found is None:
            return GapDynamicsResult(reasons=("NO_GAP",))

        idx, direction, gap_low, gap_high = found
        gap_size = max(gap_high - gap_low, 0.0)
        gap_mid = (gap_low + gap_high) / 2.0

        prior = closed[max(0, idx - self.TREND_WINDOW):idx]
        follow = closed[idx + 1: idx + 1 + self.FOLLOW_THROUGH_BARS]

        trend_dir, trend_age = self._trend_state(prior)
        ft_count = self._follow_through_count(follow, direction)
        held_open = self._gap_held_open(follow, direction, gap_low, gap_high)
        filled = self._gap_filled(closed[idx + 1:], direction, gap_low, gap_high)

        reasons = ["GAP_DETECTED"]
        breakout_strength = False
        exhaustion_risk = False
        measuring_target = 0.0

        # Brooks: classification is conditional on what happens after the gap.
        if trend_dir == "NONE" and ft_count >= 1 and held_open:
            gap_type = "BREAKAWAY_GAP"
            breakout_strength = True
            reasons += ["NEW_DIRECTION", "GAP_HELD", "FOLLOW_THROUGH"]

        elif trend_dir == direction and trend_age >= 3 and held_open and ft_count >= 1:
            gap_type = "MEASURING_GAP"
            breakout_strength = True
            reasons += ["TREND_CONTINUATION", "GAP_HELD", "MEASURING_CANDIDATE"]
            origin = self._trend_origin(prior, direction)
            if origin is not None:
                distance = abs(gap_mid - origin)
                measuring_target = gap_mid + distance if direction == "BUY" else gap_mid - distance

        elif filled and trend_dir == direction:
            gap_type = "EXHAUSTION_GAP"
            exhaustion_risk = True
            reasons += ["GAP_FILLED", "LATE_TREND_EXHAUSTION_RISK"]

        elif filled:
            gap_type = "COMMON_GAP"
            reasons += ["GAP_FILLED", "LOW_STRUCTURAL_VALUE"]

        else:
            gap_type = "UNCLASSIFIED_GAP"
            reasons.append("AWAITING_CONTEXT")

        return GapDynamicsResult(
            valid=True,
            direction=direction,
            gap_type=gap_type,
            gap_index=idx,
            gap_low=gap_low,
            gap_high=gap_high,
            gap_size=gap_size,
            gap_mid=gap_mid,
            held_open=held_open,
            filled=filled,
            follow_through_count=ft_count,
            trend_age=trend_age,
            measuring_target=measuring_target,
            breakout_strength=breakout_strength,
            exhaustion_risk=exhaustion_risk,
            reasons=tuple(reasons),
        )

    def _find_latest_gap(self, candles):
        for idx in range(len(candles) - 1, 0, -1):
            prev = candles[idx - 1]
            cur = candles[idx]
            if float(cur.low) > float(prev.high):
                return idx, "BUY", float(prev.high), float(cur.low)
            if float(cur.high) < float(prev.low):
                return idx, "SELL", float(cur.high), float(prev.low)
        return None

    def _trend_state(self, candles):
        if len(candles) < 3:
            return "NONE", 0
        ups = downs = 0
        for a, b in zip(candles, candles[1:]):
            if float(b.close) > float(a.close):
                ups += 1
            elif float(b.close) < float(a.close):
                downs += 1
        if ups >= max(3, downs + 2):
            return "BUY", ups
        if downs >= max(3, ups + 2):
            return "SELL", downs
        return "NONE", 0

    def _follow_through_count(self, bars, direction):
        count = 0
        for bar in bars:
            if direction == "BUY" and float(bar.close) > float(bar.open):
                count += 1
            elif direction == "SELL" and float(bar.close) < float(bar.open):
                count += 1
        return count

    def _gap_held_open(self, bars, direction, gap_low, gap_high):
        if not bars:
            return True
        if direction == "BUY":
            return all(float(bar.low) > gap_low for bar in bars)
        return all(float(bar.high) < gap_high for bar in bars)

    def _gap_filled(self, bars, direction, gap_low, gap_high):
        if direction == "BUY":
            return any(float(bar.low) <= gap_low for bar in bars)
        return any(float(bar.high) >= gap_high for bar in bars)

    def _trend_origin(self, prior, direction):
        if not prior:
            return None
        if direction == "BUY":
            return min(float(bar.low) for bar in prior)
        return max(float(bar.high) for bar in prior)
