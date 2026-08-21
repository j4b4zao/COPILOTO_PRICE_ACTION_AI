"""
analysis/price_action/trend_breakout_entry_dynamics.py

Brooks Trading Ranges - Chapter 4:
Breakout Entries in Strong Existing Trends.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TrendBreakoutEntryResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_SETUP"
    score: float = 0.0
    breakout_index: int = -1
    breakout_level: float = 0.0
    prior_trend_strength: float = 0.0
    pullback_bars: int = 0
    pullback_depth_ratio: float = 0.0
    breakout_body_ratio: float = 0.0
    breakout_close_extreme_ratio: float = 0.0
    follow_through_count: int = 0
    trend_aligned_breakout: bool = False
    pullback_present: bool = False
    strong_continuation: bool = False
    late_entry_risk: bool = False
    climax_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TrendBreakoutEntryDynamics:
    """Detect continuation breakouts after pullbacks in strong trends."""

    MIN_HISTORY = 12
    TREND_WINDOW = 6
    MAX_PULLBACK_BARS = 5
    FOLLOW_THROUGH_BARS = 3

    def analyze(self, candles):
        # The final candle is assumed to be current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TrendBreakoutEntryResult(reasons=("INSUFFICIENT_HISTORY",))

        setup = self._find_latest_setup(closed)
        if setup is None:
            return TrendBreakoutEntryResult(reasons=("NO_STRONG_TREND_BREAKOUT_SETUP",))

        (
            idx,
            direction,
            breakout_level,
            trend_start,
            pullback_start,
            pullback_end,
        ) = setup

        breakout = closed[idx]
        trend_bars = closed[trend_start:pullback_start]
        pullback = closed[pullback_start:pullback_end + 1]

        prior_strength = self._trend_strength(trend_bars, direction)
        pullback_depth = self._pullback_depth(trend_bars, pullback, direction)

        bar_range = max(float(breakout.high) - float(breakout.low), 1e-9)
        body_ratio = abs(float(breakout.close) - float(breakout.open)) / bar_range
        if direction == "BUY":
            close_extreme = (float(breakout.close) - float(breakout.low)) / bar_range
        else:
            close_extreme = (float(breakout.high) - float(breakout.close)) / bar_range

        follow = closed[idx + 1: idx + 1 + self.FOLLOW_THROUGH_BARS]
        ft_count = 0
        for item in follow:
            if direction == "BUY":
                aligned = float(item.close) > float(item.open) and float(item.close) >= breakout_level
            else:
                aligned = float(item.close) < float(item.open) and float(item.close) <= breakout_level
            if aligned:
                ft_count += 1

        reasons = []
        score = 0.0

        if prior_strength >= 0.80:
            score += 30; reasons.append("VERY_STRONG_PRIOR_TREND")
        elif prior_strength >= 0.65:
            score += 22; reasons.append("STRONG_PRIOR_TREND")
        elif prior_strength >= 0.55:
            score += 12

        if 1 <= len(pullback) <= 3:
            score += 15; reasons.append("SHORT_PULLBACK")
        elif len(pullback) <= self.MAX_PULLBACK_BARS:
            score += 8

        if pullback_depth <= 0.35:
            score += 15; reasons.append("SHALLOW_PULLBACK")
        elif pullback_depth <= 0.55:
            score += 8
        else:
            reasons.append("DEEP_PULLBACK")

        if body_ratio >= 0.65:
            score += 15; reasons.append("STRONG_BREAKOUT_BAR")
        elif body_ratio >= 0.50:
            score += 8

        if close_extreme >= 0.80:
            score += 10; reasons.append("BREAKOUT_CLOSE_NEAR_EXTREME")
        elif close_extreme >= 0.65:
            score += 5

        if ft_count >= 2:
            score += 15; reasons.append("FOLLOW_THROUGH")
        elif ft_count == 1:
            score += 7

        climax_risk = self._climax_risk(trend_bars, direction)
        if climax_risk:
            score -= 18; reasons.append("CLIMAX_RISK")

        late_entry_risk = pullback_depth > 0.60 or climax_risk
        if late_entry_risk:
            reasons.append("LATE_ENTRY_RISK")

        score = min(max(score, 0.0), 100.0)
        strong_continuation = (
            prior_strength >= 0.65
            and pullback_depth <= 0.55
            and body_ratio >= 0.50
            and ft_count >= 1
            and not climax_risk
        )

        if strong_continuation and score >= 75:
            state = "STRONG_TREND_BREAKOUT_ENTRY"
        elif score >= 55 and not late_entry_risk:
            state = "TREND_BREAKOUT_ENTRY_CANDIDATE"
        elif late_entry_risk:
            state = "TREND_BREAKOUT_LATE_ENTRY_RISK"
        else:
            state = "TREND_BREAKOUT_WEAK"

        return TrendBreakoutEntryResult(
            valid=True,
            direction=direction,
            state=state,
            score=score,
            breakout_index=idx,
            breakout_level=breakout_level,
            prior_trend_strength=prior_strength,
            pullback_bars=len(pullback),
            pullback_depth_ratio=pullback_depth,
            breakout_body_ratio=body_ratio,
            breakout_close_extreme_ratio=close_extreme,
            follow_through_count=ft_count,
            trend_aligned_breakout=True,
            pullback_present=bool(pullback),
            strong_continuation=strong_continuation,
            late_entry_risk=late_entry_risk,
            climax_risk=climax_risk,
            reasons=tuple(reasons),
        )

    def _find_latest_setup(self, candles):
        # Search backward for a breakout after 1-5 counter-trend pullback bars.
        for idx in range(len(candles) - 2, self.MIN_HISTORY - 2, -1):
            bar = candles[idx]

            for direction in ("BUY", "SELL"):
                pb_end = idx - 1
                if pb_end < 1:
                    continue

                pb_start = pb_end
                while pb_start > 0 and (pb_end - pb_start + 1) < self.MAX_PULLBACK_BARS:
                    item = candles[pb_start]
                    counter = (
                        float(item.close) <= float(item.open)
                        if direction == "BUY"
                        else float(item.close) >= float(item.open)
                    )
                    if not counter:
                        break
                    pb_start -= 1
                pb_start += 1

                if pb_start > pb_end:
                    continue

                trend_start = max(0, pb_start - self.TREND_WINDOW)
                trend = candles[trend_start:pb_start]
                if len(trend) < 4:
                    continue

                strength = self._trend_strength(trend, direction)
                if strength < 0.55:
                    continue

                if direction == "BUY":
                    level = max(float(x.high) for x in trend[-3:])
                    breakout = float(bar.close) > level
                else:
                    level = min(float(x.low) for x in trend[-3:])
                    breakout = float(bar.close) < level

                if breakout:
                    return idx, direction, level, trend_start, pb_start, pb_end

        return None

    @staticmethod
    def _trend_strength(bars, direction):
        if not bars:
            return 0.0
        aligned = 0
        advancing = 0
        for i, bar in enumerate(bars):
            if direction == "BUY":
                if float(bar.close) > float(bar.open):
                    aligned += 1
                if i and float(bar.close) > float(bars[i - 1].close):
                    advancing += 1
            else:
                if float(bar.close) < float(bar.open):
                    aligned += 1
                if i and float(bar.close) < float(bars[i - 1].close):
                    advancing += 1
        aligned_ratio = aligned / len(bars)
        advancing_ratio = advancing / max(len(bars) - 1, 1)
        return (aligned_ratio + advancing_ratio) / 2.0

    @staticmethod
    def _pullback_depth(trend, pullback, direction):
        if not trend or not pullback:
            return 0.0
        high = max(float(x.high) for x in trend)
        low = min(float(x.low) for x in trend)
        span = max(high - low, 1e-9)
        if direction == "BUY":
            extreme = min(float(x.low) for x in pullback)
            return max(0.0, min((high - extreme) / span, 2.0))
        extreme = max(float(x.high) for x in pullback)
        return max(0.0, min((extreme - low) / span, 2.0))

    @staticmethod
    def _climax_risk(trend, direction):
        if len(trend) < 3:
            return False
        recent = trend[-3:]
        ranges = [max(float(x.high) - float(x.low), 1e-9) for x in recent]
        bodies = [abs(float(x.close) - float(x.open)) for x in recent]
        aligned = all(
            (float(x.close) > float(x.open)) if direction == "BUY"
            else (float(x.close) < float(x.open))
            for x in recent
        )
        expanding = ranges[-1] > ranges[0] * 1.5
        large_bodies = sum(b / r >= 0.70 for b, r in zip(bodies, ranges)) >= 2
        return aligned and expanding and large_bodies
