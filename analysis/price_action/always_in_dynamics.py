"""
analysis/price_action/always_in_dynamics.py

Brooks Reversals - Chapter 15: Always In.
Diagnostic-only layer for directional market control.

This module never forces a trade. It estimates which side currently has
control and whether a convincing flip is developing.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class AlwaysInResult:
    valid: bool = False
    status: str = "ALWAYS_IN_UNCLEAR"
    direction: str = "NONE"
    previous_direction: str = "NONE"
    directional_bars: int = 0
    consecutive_bars: int = 0
    strong_bars: int = 0
    breakout: bool = False
    follow_through: bool = False
    possible_flip: bool = False
    flip_confirmed: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class AlwaysInDynamics:
    """Estimate Always-In direction from closed bars only."""

    MIN_HISTORY = 8

    def analyze(self, candles, *, previous_direction="NONE"):
        closed = list(candles[:-1]) if candles else []
        previous = self._normalize_direction(previous_direction)

        if len(closed) < self.MIN_HISTORY:
            return AlwaysInResult(
                previous_direction=previous,
                reasons=("INSUFFICIENT_HISTORY",),
            )

        recent = closed[-8:]
        ranges = [max(float(c.high) - float(c.low), 0.0) for c in recent]
        avg_range = sum(ranges) / max(len(ranges), 1)

        bull = [c for c in recent if float(c.close) > float(c.open)]
        bear = [c for c in recent if float(c.close) < float(c.open)]

        bull_strong = sum(self._strong_bar(c, "BUY", avg_range) for c in recent)
        bear_strong = sum(self._strong_bar(c, "SELL", avg_range) for c in recent)

        bull_consecutive = self._consecutive(recent, "BUY")
        bear_consecutive = self._consecutive(recent, "SELL")

        prior = recent[:-2] if len(recent) >= 3 else recent[:-1]
        last_two = recent[-2:]

        prior_high = max((float(c.high) for c in prior), default=float(recent[0].high))
        prior_low = min((float(c.low) for c in prior), default=float(recent[0].low))

        up_break = float(last_two[0].close) > prior_high
        down_break = float(last_two[0].close) < prior_low

        up_follow = (
            up_break
            and float(last_two[1].close) > float(last_two[1].open)
            and float(last_two[1].close) >= float(last_two[0].close)
        )
        down_follow = (
            down_break
            and float(last_two[1].close) < float(last_two[1].open)
            and float(last_two[1].close) <= float(last_two[0].close)
        )

        bull_score = len(bull) * 7 + bull_strong * 12 + min(bull_consecutive, 3) * 8
        bear_score = len(bear) * 7 + bear_strong * 12 + min(bear_consecutive, 3) * 8

        if up_break:
            bull_score += 14
        if up_follow:
            bull_score += 18
        if down_break:
            bear_score += 14
        if down_follow:
            bear_score += 18

        direction = "NONE"
        status = "ALWAYS_IN_UNCLEAR"

        if bull_score >= 58 and bull_score >= bear_score + 16:
            direction = "BUY"
            status = "ALWAYS_IN_LONG"
        elif bear_score >= 58 and bear_score >= bull_score + 16:
            direction = "SELL"
            status = "ALWAYS_IN_SHORT"

        opposite_break = (
            previous == "BUY" and down_break
            or previous == "SELL" and up_break
        )
        opposite_follow = (
            previous == "BUY" and down_follow
            or previous == "SELL" and up_follow
        )

        possible_flip = previous in {"BUY", "SELL"} and opposite_break
        flip_confirmed = possible_flip and opposite_follow and direction not in {"NONE", previous}

        if possible_flip and not flip_confirmed:
            status = "POSSIBLE_FLIP"
            direction = previous

        if flip_confirmed:
            status = "ALWAYS_IN_LONG" if direction == "BUY" else "ALWAYS_IN_SHORT"

        dominant = max(bull_score, bear_score)
        quality = min(100.0, dominant)

        reasons = []
        if direction == "BUY":
            reasons.append("BUY_SIDE_CONTROL")
        elif direction == "SELL":
            reasons.append("SELL_SIDE_CONTROL")
        else:
            reasons.append("NO_CLEAR_DIRECTIONAL_CONTROL")

        if up_break:
            reasons.append("UP_BREAKOUT")
        if down_break:
            reasons.append("DOWN_BREAKOUT")
        if up_follow:
            reasons.append("UP_FOLLOW_THROUGH")
        if down_follow:
            reasons.append("DOWN_FOLLOW_THROUGH")
        if possible_flip:
            reasons.append("OPPOSITE_BREAKOUT_POSSIBLE_FLIP")
        if flip_confirmed:
            reasons.append("ALWAYS_IN_FLIP_CONFIRMED")

        directional_bars = len(bull) if direction == "BUY" else len(bear) if direction == "SELL" else max(len(bull), len(bear))
        consecutive = bull_consecutive if direction == "BUY" else bear_consecutive if direction == "SELL" else max(bull_consecutive, bear_consecutive)
        strong = bull_strong if direction == "BUY" else bear_strong if direction == "SELL" else max(bull_strong, bear_strong)

        return AlwaysInResult(
            valid=True,
            status=status,
            direction=direction,
            previous_direction=previous,
            directional_bars=directional_bars,
            consecutive_bars=consecutive,
            strong_bars=strong,
            breakout=up_break or down_break,
            follow_through=up_follow or down_follow,
            possible_flip=possible_flip,
            flip_confirmed=flip_confirmed,
            quality_score=round(quality, 1),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _strong_bar(candle, direction, avg_range):
        rng = max(float(candle.high) - float(candle.low), 0.0)
        if rng <= 0:
            return 0
        body = abs(float(candle.close) - float(candle.open))
        body_ratio = body / rng
        expanded = rng >= avg_range * 0.9 if avg_range > 0 else True
        if direction == "BUY":
            directional = float(candle.close) > float(candle.open)
            close_near_extreme = (float(candle.high) - float(candle.close)) <= rng * 0.25
        else:
            directional = float(candle.close) < float(candle.open)
            close_near_extreme = (float(candle.close) - float(candle.low)) <= rng * 0.25
        return int(directional and body_ratio >= 0.55 and close_near_extreme and expanded)

    @staticmethod
    def _consecutive(candles, direction):
        count = 0
        for candle in reversed(candles):
            bullish = float(candle.close) > float(candle.open)
            bearish = float(candle.close) < float(candle.open)
            if (direction == "BUY" and bullish) or (direction == "SELL" and bearish):
                count += 1
            else:
                break
        return count

    @staticmethod
    def _normalize_direction(value):
        if value is None:
            return "NONE"
        if hasattr(value, "name"):
            value = value.name
        text = str(value).upper().strip()
        if text in {"BUY", "LONG", "UP", "BULL", "BULLISH", "ALWAYS_IN_LONG"}:
            return "BUY"
        if text in {"SELL", "SHORT", "DOWN", "BEAR", "BEARISH", "ALWAYS_IN_SHORT"}:
            return "SELL"
        return "NONE"
