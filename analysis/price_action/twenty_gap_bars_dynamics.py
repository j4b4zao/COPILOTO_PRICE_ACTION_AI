"""
analysis/price_action/twenty_gap_bars_dynamics.py

Brooks Trading Ranges - Chapter 13: Twenty Gap Bars.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TwentyGapBarsResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_SETUP"
    gap_bar_count: int = 0
    ema_period: int = 20
    ema_value: float = 0.0
    first_touch: bool = False
    crossed_ema: bool = False
    overshoot_ratio: float = 0.0
    reaction_confirmed: bool = False
    prior_trend_reversal: bool = False
    prior_extreme: float = 0.0
    distance_to_prior_extreme: float = 0.0
    continuation_bias: bool = False
    stretched_trend: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TwentyGapBarsDynamics:
    """Detect Brooks' 20-gap-bar setup around a 20-bar EMA."""

    EMA_PERIOD = 20
    MIN_GAP_BARS = 20
    MIN_HISTORY = 26

    def analyze(self, candles):
        # The last candle is assumed to be current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TwentyGapBarsResult(reasons=("INSUFFICIENT_HISTORY",))

        ema = self._ema_series(closed, self.EMA_PERIOD)
        direction, gap_count, first_touch_index = self._detect_gap_sequence(closed, ema)

        if direction == "NONE" or gap_count < self.MIN_GAP_BARS:
            return TwentyGapBarsResult(
                gap_bar_count=gap_count,
                ema_period=self.EMA_PERIOD,
                ema_value=ema[-1],
                reasons=("NO_TWENTY_GAP_SEQUENCE",),
            )

        prior_reversal = self._clear_prior_reversal(closed, direction, first_touch_index)
        first_touch = first_touch_index is not None
        crossed = False
        overshoot_ratio = 0.0
        reaction_confirmed = False
        prior_extreme = self._prior_extreme(closed, direction, first_touch_index)
        atr = max(self._average_range(closed[-20:]), 1e-9)

        if first_touch:
            touch_bar = closed[first_touch_index]
            ema_at_touch = ema[first_touch_index]
            if direction == "UP":
                crossed = float(touch_bar.low) < ema_at_touch
                overshoot_ratio = max(ema_at_touch - float(touch_bar.low), 0.0) / atr
                reaction_confirmed = self._bull_reaction(closed, first_touch_index, ema)
            else:
                crossed = float(touch_bar.high) > ema_at_touch
                overshoot_ratio = max(float(touch_bar.high) - ema_at_touch, 0.0) / atr
                reaction_confirmed = self._bear_reaction(closed, first_touch_index, ema)

        current_close = float(closed[-1].close)
        distance_to_extreme = abs(prior_extreme - current_close) if prior_extreme else 0.0
        stretched = gap_count >= self.MIN_GAP_BARS
        continuation_bias = first_touch and reaction_confirmed and not prior_reversal

        if prior_reversal:
            state = "REVERSAL_PRECEDES_TOUCH"
        elif not first_touch:
            state = "TWENTY_GAP_ACTIVE"
        elif reaction_confirmed:
            state = "FIRST_TOUCH_REACTION_CONFIRMED"
        elif crossed:
            state = "FIRST_TOUCH_OVERSHOOT_WAIT"
        else:
            state = "FIRST_TOUCH_WAIT"

        reasons = [f"TREND_{direction}", "TWENTY_GAP_BARS"]
        if first_touch:
            reasons.append("FIRST_EMA_TOUCH")
        if crossed:
            reasons.append("EMA_OVERSHOOT")
        if reaction_confirmed:
            reasons.append("PRICE_ACTION_REACTION_CONFIRMED")
        if prior_reversal:
            reasons.append("CLEAR_PRIOR_REVERSAL")

        return TwentyGapBarsResult(
            valid=True,
            direction=direction,
            state=state,
            gap_bar_count=gap_count,
            ema_period=self.EMA_PERIOD,
            ema_value=ema[-1],
            first_touch=first_touch,
            crossed_ema=crossed,
            overshoot_ratio=round(overshoot_ratio, 3),
            reaction_confirmed=reaction_confirmed,
            prior_trend_reversal=prior_reversal,
            prior_extreme=prior_extreme,
            distance_to_prior_extreme=distance_to_extreme,
            continuation_bias=continuation_bias,
            stretched_trend=stretched,
            reasons=tuple(reasons),
        )

    def _detect_gap_sequence(self, candles, ema):
        # Find the latest run of bars entirely on one side of the EMA and then
        # the first subsequent touch, if any.
        best_direction = "NONE"
        best_count = 0
        first_touch = None

        for start in range(max(self.EMA_PERIOD - 1, 0), len(candles)):
            for direction in ("UP", "DOWN"):
                count = 0
                idx = start
                while idx < len(candles):
                    bar = candles[idx]
                    level = ema[idx]
                    gap = (
                        float(bar.low) > level
                        if direction == "UP"
                        else float(bar.high) < level
                    )
                    if not gap:
                        break
                    count += 1
                    idx += 1

                if count > best_count:
                    best_count = count
                    best_direction = direction
                    first_touch = idx if idx < len(candles) else None

        return best_direction, best_count, first_touch

    def _clear_prior_reversal(self, candles, direction, touch_idx):
        end = touch_idx if touch_idx is not None else len(candles)
        sample = candles[max(0, end - 8):end]
        if len(sample) < 5:
            return False
        closes = [float(x.close) for x in sample]
        atr = self._average_range(sample)
        if direction == "UP":
            return closes[-1] < closes[0] - (1.5 * atr)
        return closes[-1] > closes[0] + (1.5 * atr)

    def _prior_extreme(self, candles, direction, touch_idx):
        end = touch_idx if touch_idx is not None else len(candles)
        sample = candles[max(0, end - 30):end]
        if not sample:
            return 0.0
        if direction == "UP":
            return max(float(x.high) for x in sample)
        return min(float(x.low) for x in sample)

    def _bull_reaction(self, candles, touch_idx, ema):
        follow = candles[touch_idx:min(len(candles), touch_idx + 4)]
        if len(follow) < 2:
            return False
        return any(
            float(bar.close) > float(bar.open)
            and float(bar.close) > ema[touch_idx + offset]
            for offset, bar in enumerate(follow)
        ) and float(follow[-1].close) > float(follow[0].close)

    def _bear_reaction(self, candles, touch_idx, ema):
        follow = candles[touch_idx:min(len(candles), touch_idx + 4)]
        if len(follow) < 2:
            return False
        return any(
            float(bar.close) < float(bar.open)
            and float(bar.close) < ema[touch_idx + offset]
            for offset, bar in enumerate(follow)
        ) and float(follow[-1].close) < float(follow[0].close)

    @staticmethod
    def _ema_series(candles, period):
        alpha = 2.0 / (period + 1.0)
        values = []
        ema = float(candles[0].close)
        for bar in candles:
            close = float(bar.close)
            ema = (close * alpha) + (ema * (1.0 - alpha))
            values.append(ema)
        return values

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
