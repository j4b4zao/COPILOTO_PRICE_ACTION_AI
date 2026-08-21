"""
analysis/price_action/first_ma_gap_bar_dynamics.py

Brooks Trading Ranges - Chapter 14:
First Moving Average Gap Bars.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class FirstMAGapBarResult:
    valid: bool = False
    trend_direction: str = "NONE"
    state: str = "NO_SETUP"
    gap_bar_index: int = -1
    gap_bar_side: str = "NONE"
    ema_value: float = 0.0
    gap_distance: float = 0.0
    gap_distance_atr: float = 0.0
    prior_extreme: float = 0.0
    signal_bar_quality: float = 0.0
    reaction_confirmed: bool = False
    continuation_bias: bool = False
    reversal_risk: bool = False
    failed_signal: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class FirstMAGapBarDynamics:
    """Detect the first bar fully beyond the EMA after a mature trend pullback."""

    MIN_HISTORY = 24
    EMA_PERIOD = 20
    LOOKBACK = 30

    def analyze(self, candles):
        # The last candle is assumed to be forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return FirstMAGapBarResult(reasons=("INSUFFICIENT_HISTORY",))

        ema = self._ema_series(closed)
        direction = self._infer_prior_trend(closed)
        if direction == "NONE":
            return FirstMAGapBarResult(reasons=("NO_CLEAR_PRIOR_TREND",))

        gap_idx = self._find_first_opposite_gap_bar(closed, ema, direction)
        if gap_idx is None:
            return FirstMAGapBarResult(
                trend_direction=direction,
                reasons=("NO_FIRST_MA_GAP_BAR",),
            )

        bar = closed[gap_idx]
        ema_value = ema[gap_idx]
        atr = max(self._average_range(closed[max(0, gap_idx - 9): gap_idx + 1]), 1e-9)

        if direction == "UP":
            gap_distance = max(ema_value - float(bar.high), 0.0)
            gap_side = "BELOW_EMA"
            prior_extreme = max(float(x.high) for x in closed[:gap_idx])
        else:
            gap_distance = max(float(bar.low) - ema_value, 0.0)
            gap_side = "ABOVE_EMA"
            prior_extreme = min(float(x.low) for x in closed[:gap_idx])

        quality = self._signal_quality(bar, direction)
        post = closed[gap_idx + 1:]
        reaction_confirmed = self._reaction_confirmed(bar, post, direction)
        failed_signal = self._signal_failed(bar, post, direction)
        reversal_risk = failed_signal or self._opposite_follow_through(post, direction)
        continuation_bias = reaction_confirmed and not reversal_risk

        if failed_signal:
            state = "FIRST_MA_GAP_SIGNAL_FAILED"
        elif reaction_confirmed:
            state = "FIRST_MA_GAP_REACTION_CONFIRMED"
        elif post:
            state = "FIRST_MA_GAP_WAIT_CONFIRMATION"
        else:
            state = "FIRST_MA_GAP_BAR"

        reasons = [
            f"PRIOR_TREND_{direction}",
            "FIRST_BAR_FULLY_OPPOSITE_EMA",
        ]
        if reaction_confirmed:
            reasons.append("REACTION_CONFIRMED")
        if failed_signal:
            reasons.append("SIGNAL_FAILED")
        if reversal_risk:
            reasons.append("REVERSAL_RISK")
        if continuation_bias:
            reasons.append("PRIOR_EXTREME_RETEST_BIAS")

        return FirstMAGapBarResult(
            valid=True,
            trend_direction=direction,
            state=state,
            gap_bar_index=gap_idx,
            gap_bar_side=gap_side,
            ema_value=ema_value,
            gap_distance=gap_distance,
            gap_distance_atr=gap_distance / atr,
            prior_extreme=prior_extreme,
            signal_bar_quality=quality,
            reaction_confirmed=reaction_confirmed,
            continuation_bias=continuation_bias,
            reversal_risk=reversal_risk,
            failed_signal=failed_signal,
            reasons=tuple(reasons),
        )

    def _infer_prior_trend(self, candles):
        # Use the earlier part of the lookback so the corrective move that creates
        # the first opposite-side EMA gap does not erase the original trend.
        sample = candles[-self.LOOKBACK:]
        if len(sample) < 18:
            return "NONE"
        anchor = sample[: max(12, len(sample) - 8)]
        closes = [float(x.close) for x in anchor]
        avg_range = max(self._average_range(anchor), 1e-9)
        delta = closes[-1] - closes[0]
        aligned_up = sum(float(x.close) > float(x.open) for x in anchor) / len(anchor)
        aligned_down = sum(float(x.close) < float(x.open) for x in anchor) / len(anchor)

        if delta >= avg_range * 3.0 and aligned_up >= 0.50:
            return "UP"
        if delta <= -avg_range * 3.0 and aligned_down >= 0.50:
            return "DOWN"
        return "NONE"

    def _find_first_opposite_gap_bar(self, candles, ema, direction):
        start = max(self.EMA_PERIOD - 1, len(candles) - self.LOOKBACK)
        found_prior_touch = False

        for i in range(start, len(candles)):
            bar = candles[i]
            level = ema[i]

            # A meaningful first gap bar should come after price has at least
            # reached/crossed the EMA during the deeper pullback.
            if float(bar.low) <= level <= float(bar.high):
                found_prior_touch = True
                continue

            if not found_prior_touch:
                continue

            if direction == "UP" and float(bar.high) < level:
                return i
            if direction == "DOWN" and float(bar.low) > level:
                return i

        return None

    @staticmethod
    def _signal_quality(bar, direction):
        rng = max(float(bar.high) - float(bar.low), 1e-9)
        body = abs(float(bar.close) - float(bar.open))
        body_ratio = body / rng

        if direction == "UP":
            close_location = (float(bar.close) - float(bar.low)) / rng
            directional = float(bar.close) >= float(bar.open)
        else:
            close_location = (float(bar.high) - float(bar.close)) / rng
            directional = float(bar.close) <= float(bar.open)

        score = 35.0 + min(body_ratio, 1.0) * 30.0 + min(max(close_location, 0.0), 1.0) * 25.0
        if directional:
            score += 10.0
        return round(min(score, 100.0), 1)

    @staticmethod
    def _reaction_confirmed(gap_bar, post, direction):
        if not post:
            return False
        first_two = post[:2]
        if direction == "UP":
            return any(float(x.close) > float(gap_bar.high) for x in first_two)
        return any(float(x.close) < float(gap_bar.low) for x in first_two)

    @staticmethod
    def _signal_failed(gap_bar, post, direction):
        if not post:
            return False
        first_three = post[:3]
        if direction == "UP":
            return any(float(x.close) < float(gap_bar.low) for x in first_three)
        return any(float(x.close) > float(gap_bar.high) for x in first_three)

    @staticmethod
    def _opposite_follow_through(post, direction):
        if len(post) < 2:
            return False
        first_two = post[:2]
        if direction == "UP":
            return all(float(x.close) < float(x.open) for x in first_two)
        return all(float(x.close) > float(x.open) for x in first_two)

    def _ema_series(self, candles):
        alpha = 2.0 / (self.EMA_PERIOD + 1.0)
        values = []
        ema = float(candles[0].close)
        for bar in candles:
            close = float(bar.close)
            ema = alpha * close + (1.0 - alpha) * ema
            values.append(ema)
        return values

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(x.high) - float(x.low), 0.0) for x in candles) / len(candles)
