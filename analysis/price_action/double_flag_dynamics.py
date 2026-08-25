"""
analysis/price_action/double_flag_dynamics.py

Brooks Trading Ranges - Chapter 12:
Double Top Bear Flags and Double Bottom Bull Flags.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class DoubleFlagResult:
    valid: bool = False
    direction: str = "NONE"
    pattern: str = "NONE"
    state: str = "NO_PATTERN"
    first_pivot_index: int = -1
    second_pivot_index: int = -1
    first_pivot_price: float = 0.0
    second_pivot_price: float = 0.0
    neckline_price: float = 0.0
    pivot_distance: float = 0.0
    pivot_distance_ratio: float = 0.0
    separation_bars: int = 0
    trend_context: bool = False
    level_match: bool = False
    resumed_trend: bool = False
    failed_pattern: bool = False
    quality_score: float = 0.0
    continuation_bias: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class DoubleFlagDynamics:
    """Detect double-top bear flags and double-bottom bull flags."""

    MIN_HISTORY = 14
    LOOKBACK = 24
    MIN_SEPARATION = 2
    MAX_SEPARATION = 12
    PIVOT_TOLERANCE_ATR = 0.45

    def analyze(self, candles):
        # The last candle is assumed to be current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return DoubleFlagResult(
                reasons=("INSUFFICIENT_HISTORY",),
            )

        direction = self._infer_trend(closed)
        if direction == "NONE":
            return DoubleFlagResult(
                reasons=("NO_CLEAR_TREND",),
            )

        sample_start = max(0, len(closed) - self.LOOKBACK)
        sample = closed[sample_start:]
        atr = max(self._average_range(sample), 1e-9)

        if direction == "DOWN":
            candidate = self._find_double_top(sample, atr)
            pattern = "DOUBLE_TOP_BEAR_FLAG"
        else:
            candidate = self._find_double_bottom(sample, atr)
            pattern = "DOUBLE_BOTTOM_BULL_FLAG"

        if candidate is None:
            return DoubleFlagResult(
                direction=direction,
                trend_context=True,
                reasons=(f"TREND_{direction}", "NO_DOUBLE_FLAG"),
            )

        p1, p2, price1, price2, neckline = candidate
        global_p1 = sample_start + p1
        global_p2 = sample_start + p2
        distance = abs(price2 - price1)
        distance_ratio = distance / atr
        level_match = distance_ratio <= self.PIVOT_TOLERANCE_ATR

        bars_after = closed[global_p2 + 1:]
        resumed, failed = self._confirmation(
            direction,
            bars_after,
            neckline,
            price1,
            price2,
        )

        if failed:
            state = "DOUBLE_FLAG_FAILED"
        elif resumed:
            state = "DOUBLE_FLAG_CONFIRMED"
        else:
            state = "DOUBLE_FLAG_CANDIDATE"

        separation = global_p2 - global_p1
        score = 40.0
        if level_match:
            score += 25.0
        if self.MIN_SEPARATION <= separation <= self.MAX_SEPARATION:
            score += 10.0
        if resumed:
            score += 25.0
        if failed:
            score -= 35.0
        score = max(0.0, min(score, 100.0))

        reasons = [
            f"TREND_{direction}",
            pattern,
            "TWO_TESTS_NEAR_SAME_LEVEL",
        ]
        if resumed:
            reasons.append("TREND_RESUMPTION_CONFIRMED")
        if failed:
            reasons.append("FLAG_INVALIDATED")

        return DoubleFlagResult(
            valid=level_match and not failed,
            direction=direction,
            pattern=pattern,
            state=state,
            first_pivot_index=global_p1,
            second_pivot_index=global_p2,
            first_pivot_price=price1,
            second_pivot_price=price2,
            neckline_price=neckline,
            pivot_distance=distance,
            pivot_distance_ratio=distance_ratio,
            separation_bars=separation,
            trend_context=True,
            level_match=level_match,
            resumed_trend=resumed,
            failed_pattern=failed,
            quality_score=round(score, 1),
            continuation_bias=resumed and not failed,
            reasons=tuple(reasons),
        )

    def _infer_trend(self, candles):
        # Use the broader closed-bar context so the flag itself does not have
        # to look directional. This is a continuation pattern.
        sample = candles[-14:]
        if len(sample) < 10:
            return "NONE"

        avg_range = self._average_range(sample)
        closes = [float(x.close) for x in sample]
        early = sum(closes[:5]) / 5.0
        late = sum(closes[-5:]) / 5.0
        delta = late - early

        if delta >= avg_range * 1.15:
            return "UP"
        if delta <= -avg_range * 1.15:
            return "DOWN"
        return "NONE"

    def _find_double_top(self, candles, atr):
        pivots = self._swing_highs(candles)
        for right_pos in range(len(pivots) - 1, 0, -1):
            p2 = pivots[right_pos]
            for left_pos in range(right_pos - 1, -1, -1):
                p1 = pivots[left_pos]
                separation = p2 - p1
                if separation < self.MIN_SEPARATION:
                    continue
                if separation > self.MAX_SEPARATION:
                    break
                price1 = float(candles[p1].high)
                price2 = float(candles[p2].high)
                if abs(price2 - price1) > atr * self.PIVOT_TOLERANCE_ATR:
                    continue
                middle = candles[p1 + 1:p2]
                if not middle:
                    continue
                neckline = min(float(x.low) for x in middle)
                return p1, p2, price1, price2, neckline
        return None

    def _find_double_bottom(self, candles, atr):
        pivots = self._swing_lows(candles)
        for right_pos in range(len(pivots) - 1, 0, -1):
            p2 = pivots[right_pos]
            for left_pos in range(right_pos - 1, -1, -1):
                p1 = pivots[left_pos]
                separation = p2 - p1
                if separation < self.MIN_SEPARATION:
                    continue
                if separation > self.MAX_SEPARATION:
                    break
                price1 = float(candles[p1].low)
                price2 = float(candles[p2].low)
                if abs(price2 - price1) > atr * self.PIVOT_TOLERANCE_ATR:
                    continue
                middle = candles[p1 + 1:p2]
                if not middle:
                    continue
                neckline = max(float(x.high) for x in middle)
                return p1, p2, price1, price2, neckline
        return None

    @staticmethod
    def _swing_highs(candles):
        result = []
        for i in range(1, len(candles) - 1):
            high = float(candles[i].high)
            if high >= float(candles[i - 1].high) and high > float(candles[i + 1].high):
                result.append(i)
        return result

    @staticmethod
    def _swing_lows(candles):
        result = []
        for i in range(1, len(candles) - 1):
            low = float(candles[i].low)
            if low <= float(candles[i - 1].low) and low < float(candles[i + 1].low):
                result.append(i)
        return result

    @staticmethod
    def _confirmation(direction, bars_after, neckline, price1, price2):
        if not bars_after:
            return False, False

        if direction == "DOWN":
            resumed = any(float(x.close) < neckline for x in bars_after)
            invalidation = max(price1, price2)
            failed = any(float(x.close) > invalidation for x in bars_after)
            return resumed, failed

        resumed = any(float(x.close) > neckline for x in bars_after)
        invalidation = min(price1, price2)
        failed = any(float(x.close) < invalidation for x in bars_after)
        return resumed, failed

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
