"""
analysis/price_action/reversal_trade_example_dynamics.py

Brooks Price Action Reversals - Chapter 1:
Example of How to Trade a Reversal.

Diagnostic-only layer. It models the structural sequence of a tradable reversal
without mutating Score/Risk/Decision or sending orders.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ReversalTradeExampleResult:
    valid: bool = False
    old_trend: str = "NONE"
    reversal_direction: str = "NONE"
    state: str = "NO_REVERSAL"
    trend_exhaustion: bool = False
    structural_break: bool = False
    extreme_test: bool = False
    micro_double: bool = False
    opposite_pressure: bool = False
    reversal_confirmed: bool = False
    range_only_risk: bool = False
    quality_score: float = 0.0
    test_level: float = 0.0
    break_level: float = 0.0
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ReversalTradeExampleDynamics:
    """Model trend -> structural break -> extreme test -> opposite trend confirmation."""

    MIN_HISTORY = 10
    SWING = 2
    TEST_TOLERANCE_RATIO = 0.35
    STRONG_BODY_RATIO = 0.55

    def analyze(self, candles, old_trend=None):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ReversalTradeExampleResult(
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        trend = str(old_trend or self._infer_old_trend(closed)).upper()
        if trend not in ("UP", "DOWN"):
            return ReversalTradeExampleResult(
                reason="OLD_TREND_UNCLEAR",
                reasons=("OLD_TREND_UNCLEAR",),
            )

        direction = "SELL" if trend == "UP" else "BUY"
        ranges = [max(float(c.high) - float(c.low), 0.0) for c in closed]
        avg_range = sum(ranges[-8:]) / max(len(ranges[-8:]), 1)
        tolerance = max(avg_range * self.TEST_TOLERANCE_RATIO, 1e-9)

        swing_highs, swing_lows = self._pivots(closed)
        reasons = []

        exhaustion = self._trend_exhaustion(closed, trend)
        if exhaustion:
            reasons.append("OLD_TREND_SHOWS_EXHAUSTION")

        structural_break, break_level, break_index = self._structural_break(
            closed, trend, swing_highs, swing_lows
        )
        if structural_break:
            reasons.append("COUNTERTREND_STRUCTURAL_BREAK")

        extreme_test, test_level, test_index, micro_double = self._extreme_test(
            closed,
            trend,
            swing_highs,
            swing_lows,
            break_index,
            tolerance,
        )
        if extreme_test:
            reasons.append("OLD_EXTREME_TESTED_AFTER_BREAK")
        if micro_double:
            reasons.append("MICRO_DOUBLE_REVERSAL_STRUCTURE")

        opposite_pressure = self._opposite_pressure(closed, direction, test_index)
        if opposite_pressure:
            reasons.append("OPPOSITE_PRESSURE_CONFIRMED")

        confirmed = structural_break and extreme_test and opposite_pressure
        range_only_risk = structural_break and extreme_test and not opposite_pressure
        if range_only_risk:
            reasons.append("REVERSAL_MAY_ONLY_BECOME_TRADING_RANGE")

        if confirmed:
            state = "REVERSAL_CONFIRMED"
        elif structural_break and extreme_test:
            state = "EXTREME_TEST"
        elif structural_break:
            state = "STRUCTURAL_BREAK"
        elif exhaustion:
            state = "REVERSAL_WATCH"
        else:
            state = "NO_REVERSAL"

        score = 0.0
        score += 15.0 if exhaustion else 0.0
        score += 30.0 if structural_break else 0.0
        score += 25.0 if extreme_test else 0.0
        score += 10.0 if micro_double else 0.0
        score += 20.0 if opposite_pressure else 0.0
        if range_only_risk:
            score = min(score, 65.0)

        if not reasons:
            reasons.append("NO_REVERSAL_SEQUENCE_CONFIRMED")

        return ReversalTradeExampleResult(
            valid=True,
            old_trend=trend,
            reversal_direction=direction,
            state=state,
            trend_exhaustion=exhaustion,
            structural_break=structural_break,
            extreme_test=extreme_test,
            micro_double=micro_double,
            opposite_pressure=opposite_pressure,
            reversal_confirmed=confirmed,
            range_only_risk=range_only_risk,
            quality_score=round(min(score, 100.0), 1),
            test_level=round(test_level, 8) if test_level else 0.0,
            break_level=round(break_level, 8) if break_level else 0.0,
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    def _infer_old_trend(self, candles):
        sample = candles[: max(6, len(candles) // 2)]
        if len(sample) < 4:
            return "NONE"
        delta = float(sample[-1].close) - float(sample[0].close)
        avg_range = sum(float(c.high) - float(c.low) for c in sample) / len(sample)
        if delta > avg_range:
            return "UP"
        if delta < -avg_range:
            return "DOWN"
        return "NONE"

    def _pivots(self, candles):
        highs = []
        lows = []
        s = self.SWING
        for i in range(s, len(candles) - s):
            h = float(candles[i].high)
            l = float(candles[i].low)
            if all(h > float(candles[j].high) for j in range(i - s, i + s + 1) if j != i):
                highs.append((i, h))
            if all(l < float(candles[j].low) for j in range(i - s, i + s + 1) if j != i):
                lows.append((i, l))
        return highs, lows

    def _trend_exhaustion(self, candles, trend):
        recent = candles[-5:]
        opposite = 0
        tails = 0
        for c in recent:
            o, h, l, cl = map(float, (c.open, c.high, c.low, c.close))
            rng = max(h - l, 1e-9)
            if trend == "UP":
                opposite += int(cl < o)
                tails += int((h - max(o, cl)) / rng >= 0.35)
            else:
                opposite += int(cl > o)
                tails += int((min(o, cl) - l) / rng >= 0.35)
        return opposite >= 2 or tails >= 2

    def _structural_break(self, candles, trend, swing_highs, swing_lows):
        if trend == "UP":
            candidates = [(i, p) for i, p in swing_lows if i < len(candles) - 1]
            if not candidates:
                return False, 0.0, None
            i, level = candidates[-1]
            for j in range(i + 1, len(candles)):
                if float(candles[j].close) < level:
                    return True, level, j
        else:
            candidates = [(i, p) for i, p in swing_highs if i < len(candles) - 1]
            if not candidates:
                return False, 0.0, None
            i, level = candidates[-1]
            for j in range(i + 1, len(candles)):
                if float(candles[j].close) > level:
                    return True, level, j
        return False, 0.0, None

    def _extreme_test(self, candles, trend, swing_highs, swing_lows, break_index, tolerance):
        if break_index is None:
            return False, 0.0, None, False

        if trend == "UP":
            prior = [(i, p) for i, p in swing_highs if i < break_index]
            if not prior:
                return False, 0.0, None, False
            extreme_i, extreme = prior[-1]
            for j in range(break_index + 1, len(candles)):
                if abs(float(candles[j].high) - extreme) <= tolerance or float(candles[j].high) >= extreme:
                    return True, extreme, j, (j - extreme_i) <= 6
        else:
            prior = [(i, p) for i, p in swing_lows if i < break_index]
            if not prior:
                return False, 0.0, None, False
            extreme_i, extreme = prior[-1]
            for j in range(break_index + 1, len(candles)):
                if abs(float(candles[j].low) - extreme) <= tolerance or float(candles[j].low) <= extreme:
                    return True, extreme, j, (j - extreme_i) <= 6
        return False, 0.0, None, False

    def _opposite_pressure(self, candles, direction, start_index):
        if start_index is None:
            return False
        after = candles[start_index: start_index + 4]
        strong = 0
        directional = 0
        for c in after:
            o, h, l, cl = map(float, (c.open, c.high, c.low, c.close))
            rng = max(h - l, 1e-9)
            body = abs(cl - o) / rng
            if direction == "BUY":
                ok = cl > o
                close_pos = (cl - l) / rng
            else:
                ok = cl < o
                close_pos = (h - cl) / rng
            if ok:
                directional += 1
            if ok and body >= self.STRONG_BODY_RATIO and close_pos >= 0.65:
                strong += 1
        return strong >= 1 and directional >= 2
