"""
analysis/price_action/breakout_strength_dynamics.py

Brooks Trading Ranges - Chapter 2: Signs of Strength in a Breakout.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class BreakoutStrengthResult:
    valid: bool = False
    direction: str = "NONE"
    quality: str = "NONE"
    score: float = 0.0
    breakout_index: int = -1
    breakout_level: float = 0.0
    body_ratio: float = 0.0
    close_extreme_ratio: float = 0.0
    adverse_tail_ratio: float = 0.0
    follow_through_count: int = 0
    closes_beyond_level: int = 0
    prior_bars_overcome: int = 0
    immediate_rejection: bool = False
    strong_follow_through: bool = False
    strong_breakout: bool = False
    very_strong_breakout: bool = False
    failed_breakout_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class BreakoutStrengthDynamics:
    """Classify the quality of a confirmed breakout using closed candles only."""

    MIN_HISTORY = 8
    LOOKBACK_LEVEL = 5
    FOLLOW_THROUGH_BARS = 3

    def analyze(self, candles):
        # Last element is treated as the current/forming candle and excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return BreakoutStrengthResult(reasons=("INSUFFICIENT_HISTORY",))

        candidate = self._find_latest_breakout(closed)
        if candidate is None:
            return BreakoutStrengthResult(reasons=("NO_CONFIRMED_BREAKOUT",))

        idx, direction, level = candidate
        bar = closed[idx]
        bar_range = max(float(bar.high) - float(bar.low), 1e-9)
        body = abs(float(bar.close) - float(bar.open))
        body_ratio = body / bar_range

        if direction == "BUY":
            close_extreme_ratio = (float(bar.close) - float(bar.low)) / bar_range
            adverse_tail = float(bar.high) - float(bar.close)
        else:
            close_extreme_ratio = (float(bar.high) - float(bar.close)) / bar_range
            adverse_tail = float(bar.close) - float(bar.low)
        adverse_tail_ratio = max(adverse_tail, 0.0) / bar_range

        follow = closed[idx + 1 : idx + 1 + self.FOLLOW_THROUGH_BARS]
        ft_count = 0
        closes_beyond = 0
        rejection = False

        for item in follow:
            if direction == "BUY":
                aligned = float(item.close) > float(item.open)
                beyond = float(item.close) > level
                rejected = float(item.close) < level
            else:
                aligned = float(item.close) < float(item.open)
                beyond = float(item.close) < level
                rejected = float(item.close) > level

            if aligned:
                ft_count += 1
            if beyond:
                closes_beyond += 1
            if rejected:
                rejection = True

        prior = closed[max(0, idx - 20):idx]
        if direction == "BUY":
            prior_bars_overcome = sum(float(x.close) < float(bar.close) for x in prior)
        else:
            prior_bars_overcome = sum(float(x.close) > float(bar.close) for x in prior)

        score = 0.0
        reasons = []

        if body_ratio >= 0.70:
            score += 25; reasons.append("LARGE_TREND_BODY")
        elif body_ratio >= 0.55:
            score += 18; reasons.append("GOOD_TREND_BODY")
        elif body_ratio >= 0.40:
            score += 10

        if close_extreme_ratio >= 0.85:
            score += 20; reasons.append("CLOSE_NEAR_EXTREME")
        elif close_extreme_ratio >= 0.70:
            score += 12

        if adverse_tail_ratio <= 0.10:
            score += 15; reasons.append("SMALL_ADVERSE_TAIL")
        elif adverse_tail_ratio <= 0.20:
            score += 8

        if ft_count >= 2:
            score += 15; reasons.append("FOLLOW_THROUGH")
        elif ft_count == 1:
            score += 7

        if closes_beyond >= 2:
            score += 15; reasons.append("ACCEPTANCE_BEYOND_LEVEL")
        elif closes_beyond == 1:
            score += 7

        if prior_bars_overcome >= 10:
            score += 10; reasons.append("MANY_PRIOR_CLOSES_OVERCOME")
        elif prior_bars_overcome >= 5:
            score += 5

        if rejection:
            score -= 25; reasons.append("IMMEDIATE_REJECTION")

        score = min(max(score, 0.0), 100.0)
        strong_ft = ft_count >= 2 and closes_beyond >= 2 and not rejection

        if score >= 85 and strong_ft:
            quality = "VERY_STRONG"
        elif score >= 70:
            quality = "STRONG"
        elif score >= 50:
            quality = "MODERATE"
        else:
            quality = "WEAK"

        return BreakoutStrengthResult(
            valid=True,
            direction=direction,
            quality=quality,
            score=score,
            breakout_index=idx,
            breakout_level=level,
            body_ratio=body_ratio,
            close_extreme_ratio=close_extreme_ratio,
            adverse_tail_ratio=adverse_tail_ratio,
            follow_through_count=ft_count,
            closes_beyond_level=closes_beyond,
            prior_bars_overcome=prior_bars_overcome,
            immediate_rejection=rejection,
            strong_follow_through=strong_ft,
            strong_breakout=score >= 70,
            very_strong_breakout=score >= 85 and strong_ft,
            failed_breakout_risk=rejection or closes_beyond == 0,
            reasons=tuple(reasons),
        )

    def _find_latest_breakout(self, candles):
        start = self.LOOKBACK_LEVEL
        # Require room after the breakout for follow-through evaluation.
        end = len(candles) - 1
        for idx in range(end - 1, start - 1, -1):
            previous = candles[idx - self.LOOKBACK_LEVEL:idx]
            high_level = max(float(x.high) for x in previous)
            low_level = min(float(x.low) for x in previous)
            bar = candles[idx]

            if float(bar.close) > high_level:
                return idx, "BUY", high_level
            if float(bar.close) < low_level:
                return idx, "SELL", low_level
        return None
