"""
analysis/price_action/dueling_lines_dynamics.py

Brooks Trading Ranges - Chapter 19:
Dueling Lines: Wedge Pullback to the Trend Line.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class DuelingLinesResult:
    valid: bool = False
    trend_direction: str = "NONE"
    setup_direction: str = "NONE"
    state: str = "NO_DUELING_LINES"
    wedge_three_push: bool = False
    trendline_touch: bool = False
    channel_line_touch: bool = False
    moving_average_touch: bool = False
    horizontal_level_touch: bool = False
    confluence_count: int = 0
    confluence_score: float = 0.0
    trendline_price: float = 0.0
    secondary_level_price: float = 0.0
    signal_bar_index: int = -1
    signal_quality: float = 0.0
    reaction_confirmed: bool = False
    continuation_bias: bool = False
    reversal_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class DuelingLinesDynamics:
    """Detect a three-push pullback ending at converging structural lines."""

    MIN_HISTORY = 16
    LOOKBACK = 30
    EMA_PERIOD = 20
    TOUCH_ATR = 0.35

    def analyze(self, candles):
        # The last candle is current/forming and is intentionally excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return DuelingLinesResult(reasons=("INSUFFICIENT_HISTORY",))

        trend = self._infer_trend(closed)
        if trend == "NONE":
            return DuelingLinesResult(reasons=("NO_CLEAR_TREND",))

        atr = max(self._average_range(closed[-14:]), 1e-9)
        pullback_start = self._find_pullback_start(closed, trend)
        if pullback_start is None:
            return DuelingLinesResult(
                trend_direction=trend,
                reasons=("NO_ACTIVE_PULLBACK",),
            )

        signal_idx = self._find_signal_bar(closed, pullback_start, trend)
        if signal_idx is None:
            return DuelingLinesResult(
                trend_direction=trend,
                reasons=("NO_SIGNAL_BAR",),
            )

        wedge = self._three_push_pullback(closed, pullback_start, signal_idx, trend)
        trendline_price = self._trendline_projection(closed, signal_idx, trend)
        trendline_touch = self._bar_touches_level(closed[signal_idx], trendline_price, atr)

        channel_line = self._pullback_channel_projection(
            closed,
            pullback_start,
            signal_idx,
            trend,
        )
        channel_touch = self._bar_touches_level(closed[signal_idx], channel_line, atr)

        ema = self._ema_series(closed)
        ema_level = ema[signal_idx]
        ma_touch = self._bar_touches_level(closed[signal_idx], ema_level, atr)

        horizontal = self._nearest_horizontal_level(closed, signal_idx, trend)
        horizontal_touch = self._bar_touches_level(closed[signal_idx], horizontal, atr)

        secondary_candidates = []
        if channel_touch:
            secondary_candidates.append(("CHANNEL_LINE", channel_line))
        if ma_touch:
            secondary_candidates.append(("MOVING_AVERAGE", ema_level))
        if horizontal_touch:
            secondary_candidates.append(("HORIZONTAL_LEVEL", horizontal))

        primary = wedge and trendline_touch
        confluence_count = int(trendline_touch) + len(secondary_candidates)
        secondary_level = secondary_candidates[0][1] if secondary_candidates else 0.0

        signal_quality = self._signal_quality(closed[signal_idx], trend)
        reaction = self._reaction_confirmed(closed, signal_idx, trend)
        invalidated = self._invalidated(closed, signal_idx, trend)

        confluence_score = 0.0
        if wedge:
            confluence_score += 30.0
        if trendline_touch:
            confluence_score += 30.0
        confluence_score += min(len(secondary_candidates) * 15.0, 30.0)
        confluence_score += min(signal_quality * 10.0, 10.0)
        confluence_score = min(confluence_score, 100.0)

        if invalidated:
            state = "DUELING_LINES_FAILED"
        elif primary and secondary_candidates and reaction:
            state = "DUELING_LINES_CONFIRMED"
        elif primary and secondary_candidates:
            state = "DUELING_LINES_WAIT_CONFIRMATION"
        elif wedge and (trendline_touch or secondary_candidates):
            state = "DUELING_LINES_CANDIDATE"
        else:
            state = "NO_DUELING_LINES"

        continuation_bias = state == "DUELING_LINES_CONFIRMED"
        reversal_risk = invalidated

        reasons = [f"TREND_{trend}"]
        if wedge:
            reasons.append("THREE_PUSH_WEDGE_PULLBACK")
        if trendline_touch:
            reasons.append("TRENDLINE_TOUCH")
        for name, _ in secondary_candidates:
            reasons.append(name)
        if reaction:
            reasons.append("REACTION_CONFIRMED")
        if invalidated:
            reasons.append("SETUP_INVALIDATED")
        if state == "DUELING_LINES_WAIT_CONFIRMATION":
            reasons.append("WAIT_PRICE_ACTION_CONFIRMATION")

        return DuelingLinesResult(
            valid=state != "NO_DUELING_LINES",
            trend_direction=trend,
            setup_direction="BUY" if trend == "UP" else "SELL",
            state=state,
            wedge_three_push=wedge,
            trendline_touch=trendline_touch,
            channel_line_touch=channel_touch,
            moving_average_touch=ma_touch,
            horizontal_level_touch=horizontal_touch,
            confluence_count=confluence_count,
            confluence_score=round(confluence_score, 1),
            trendline_price=round(trendline_price, 6),
            secondary_level_price=round(secondary_level, 6),
            signal_bar_index=signal_idx,
            signal_quality=round(signal_quality, 3),
            reaction_confirmed=reaction,
            continuation_bias=continuation_bias,
            reversal_risk=reversal_risk,
            reasons=tuple(reasons),
        )

    def _infer_trend(self, candles):
        sample = candles[-12:]
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        if delta >= atr * 1.5:
            return "UP"
        if delta <= -atr * 1.5:
            return "DOWN"

        highs = [float(x.high) for x in sample]
        lows = [float(x.low) for x in sample]
        if max(highs[-5:]) > max(highs[:5]) and min(lows[-5:]) > min(lows[:5]):
            return "UP"
        if max(highs[-5:]) < max(highs[:5]) and min(lows[-5:]) < min(lows[:5]):
            return "DOWN"
        return "NONE"

    def _find_pullback_start(self, candles, trend):
        start = max(3, len(candles) - self.LOOKBACK)
        if trend == "UP":
            extreme = max(range(start, len(candles) - 3), key=lambda i: float(candles[i].high))
        else:
            extreme = min(range(start, len(candles) - 3), key=lambda i: float(candles[i].low))
        return extreme if extreme < len(candles) - 3 else None

    def _find_signal_bar(self, candles, start, trend):
        for i in range(len(candles) - 2, start + 2, -1):
            bar = candles[i]
            if trend == "UP":
                rejection = float(bar.close) > float(bar.open) or (
                    float(bar.close) - float(bar.low)
                    > float(bar.high) - float(bar.close)
                )
            else:
                rejection = float(bar.close) < float(bar.open) or (
                    float(bar.high) - float(bar.close)
                    > float(bar.close) - float(bar.low)
                )
            if rejection:
                return i
        return None

    def _three_push_pullback(self, candles, start, end, trend):
        pivots = []
        for i in range(max(start + 1, 2), min(end + 1, len(candles) - 2)):
            if trend == "UP":
                low = float(candles[i].low)
                if low < float(candles[i - 1].low) and low < float(candles[i + 1].low):
                    pivots.append(low)
            else:
                high = float(candles[i].high)
                if high > float(candles[i - 1].high) and high > float(candles[i + 1].high):
                    pivots.append(high)
        if len(pivots) < 3:
            return False
        a, b, c = pivots[-3:]
        return (a > b > c) if trend == "UP" else (a < b < c)

    def _trendline_projection(self, candles, idx, trend):
        anchor_slice = candles[max(0, idx - 14):idx]
        if trend == "UP":
            pts = sorted(
                [(i, float(x.low)) for i, x in enumerate(anchor_slice)],
                key=lambda z: z[1],
            )[:2]
        else:
            pts = sorted(
                [(i, float(x.high)) for i, x in enumerate(anchor_slice)],
                key=lambda z: z[1],
                reverse=True,
            )[:2]
        if len(pts) < 2 or pts[0][0] == pts[1][0]:
            return float(candles[idx].close)
        pts.sort(key=lambda z: z[0])
        (x1, y1), (x2, y2) = pts
        slope = (y2 - y1) / (x2 - x1)
        target_x = len(anchor_slice)
        return y1 + slope * (target_x - x1)

    def _pullback_channel_projection(self, candles, start, idx, trend):
        segment = candles[start:idx + 1]
        if not segment:
            return 0.0
        return (
            min(float(x.low) for x in segment)
            if trend == "UP"
            else max(float(x.high) for x in segment)
        )

    def _nearest_horizontal_level(self, candles, idx, trend):
        history = candles[max(0, idx - 20):max(0, idx - 2)]
        if not history:
            return 0.0
        bar = candles[idx]
        if trend == "UP":
            candidates = [float(x.low) for x in history]
            return min(candidates, key=lambda p: abs(p - float(bar.low)))
        candidates = [float(x.high) for x in history]
        return min(candidates, key=lambda p: abs(p - float(bar.high)))

    def _ema_series(self, candles):
        alpha = 2.0 / (self.EMA_PERIOD + 1.0)
        ema = []
        value = float(candles[0].close)
        for bar in candles:
            value = alpha * float(bar.close) + (1.0 - alpha) * value
            ema.append(value)
        return ema

    def _bar_touches_level(self, bar, level, atr):
        if level <= 0:
            return False
        low = float(bar.low) - atr * self.TOUCH_ATR
        high = float(bar.high) + atr * self.TOUCH_ATR
        return low <= level <= high

    @staticmethod
    def _signal_quality(bar, trend):
        rng = max(float(bar.high) - float(bar.low), 1e-9)
        body = abs(float(bar.close) - float(bar.open)) / rng
        if trend == "UP":
            close_position = (float(bar.close) - float(bar.low)) / rng
        else:
            close_position = (float(bar.high) - float(bar.close)) / rng
        return max(0.0, min((body + close_position) / 2.0, 1.0))

    @staticmethod
    def _reaction_confirmed(candles, idx, trend):
        if idx + 1 >= len(candles):
            return False
        signal = candles[idx]
        follow = candles[idx + 1]
        if trend == "UP":
            return float(follow.close) > float(signal.high) or (
                float(follow.close) > float(follow.open)
                and float(follow.close) > float(signal.close)
            )
        return float(follow.close) < float(signal.low) or (
            float(follow.close) < float(follow.open)
            and float(follow.close) < float(signal.close)
        )

    @staticmethod
    def _invalidated(candles, idx, trend):
        if idx + 1 >= len(candles):
            return False
        signal = candles[idx]
        follow = candles[idx + 1]
        if trend == "UP":
            return float(follow.close) < float(signal.low)
        return float(follow.close) > float(signal.high)

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(x.high) - float(x.low), 0.0) for x in candles) / len(candles)
