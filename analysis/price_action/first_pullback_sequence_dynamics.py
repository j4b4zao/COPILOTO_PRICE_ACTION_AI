"""
analysis/price_action/first_pullback_sequence_dynamics.py

Brooks Trading Ranges - Chapter 11:
First Pullback Sequence: Bar -> Minor Trendline -> Moving Average ->
Moving Average Gap -> Major Trendline -> Trading Range.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class FirstPullbackSequenceResult:
    valid: bool = False
    direction: str = "NONE"
    stage: str = "NO_SEQUENCE"
    stage_index: int = 0
    first_pullback_bars: int = 0
    minor_trendline_break: bool = False
    moving_average_touch: bool = False
    moving_average_close_cross: bool = False
    moving_average_gap_bar: bool = False
    major_trendline_break: bool = False
    long_two_leg_pullback: bool = False
    two_sided_trading: bool = False
    trading_range_transition: bool = False
    trend_maturity_score: float = 0.0
    continuation_bias: bool = False
    reversal_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class FirstPullbackSequenceDynamics:
    """Track the progressive pullback sequence described by Brooks Ch. 11."""

    MIN_HISTORY = 14
    MA_PERIOD = 10

    STAGES = (
        "NO_SEQUENCE",
        "BAR_PULLBACK",
        "MINOR_TRENDLINE_BREAK",
        "MOVING_AVERAGE_TOUCH",
        "MOVING_AVERAGE_CROSS",
        "MOVING_AVERAGE_GAP",
        "MAJOR_TRENDLINE_BREAK",
        "LONG_TWO_LEG_PULLBACK",
        "TRADING_RANGE_TRANSITION",
    )

    def analyze(self, candles):
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return FirstPullbackSequenceResult(
                reasons=("INSUFFICIENT_HISTORY",),
            )

        direction = self._infer_direction(closed)
        if direction == "NONE":
            return FirstPullbackSequenceResult(
                reasons=("NO_CLEAR_TREND",),
            )

        ma = self._moving_average_series(closed)
        pullback_bars = self._count_first_pullback_bars(closed, direction)
        minor_break = self._minor_trendline_break(closed, direction)
        ma_touch = self._moving_average_touch(closed, ma, direction)
        ma_cross = self._moving_average_close_cross(closed, ma, direction)
        ma_gap = self._moving_average_gap_bar(closed, ma, direction)
        major_break = self._major_trendline_break(closed, direction)
        long_two_leg = self._long_two_leg_pullback(closed, direction)
        two_sided = self._two_sided_trading(closed)
        range_transition = two_sided and long_two_leg

        stage_index = 0
        reasons = [f"TREND_{direction}"]

        if pullback_bars >= 1:
            stage_index = max(stage_index, 1)
            reasons.append("FIRST_BAR_PULLBACK")
        if minor_break:
            stage_index = max(stage_index, 2)
            reasons.append("MINOR_TRENDLINE_BREAK")
        if ma_touch:
            stage_index = max(stage_index, 3)
            reasons.append("MOVING_AVERAGE_TOUCH")
        if ma_cross:
            stage_index = max(stage_index, 4)
            reasons.append("MOVING_AVERAGE_CLOSE_CROSS")
        if ma_gap:
            stage_index = max(stage_index, 5)
            reasons.append("MOVING_AVERAGE_GAP_BAR")
        if major_break:
            stage_index = max(stage_index, 6)
            reasons.append("MAJOR_TRENDLINE_BREAK")
        if long_two_leg:
            stage_index = max(stage_index, 7)
            reasons.append("LONG_TWO_LEG_PULLBACK")
        if range_transition:
            stage_index = 8
            reasons.append("TRADING_RANGE_TRANSITION")

        maturity_score = round((stage_index / 8.0) * 100.0, 1)
        continuation_bias = stage_index <= 3
        reversal_risk = stage_index >= 6

        return FirstPullbackSequenceResult(
            valid=stage_index > 0,
            direction=direction,
            stage=self.STAGES[stage_index],
            stage_index=stage_index,
            first_pullback_bars=pullback_bars,
            minor_trendline_break=minor_break,
            moving_average_touch=ma_touch,
            moving_average_close_cross=ma_cross,
            moving_average_gap_bar=ma_gap,
            major_trendline_break=major_break,
            long_two_leg_pullback=long_two_leg,
            two_sided_trading=two_sided,
            trading_range_transition=range_transition,
            trend_maturity_score=maturity_score,
            continuation_bias=continuation_bias,
            reversal_risk=reversal_risk,
            reasons=tuple(reasons),
        )

    def _infer_direction(self, candles):
        sample = candles[-10:]
        closes = [float(x.close) for x in sample]
        avg_range = self._average_range(sample)
        delta = closes[-1] - closes[0]
        if delta >= avg_range * 2.0:
            return "UP"
        if delta <= -avg_range * 2.0:
            return "DOWN"
        return "NONE"

    def _count_first_pullback_bars(self, candles, direction):
        sample = candles[-6:]
        count = 0
        for bar in reversed(sample):
            if direction == "UP" and float(bar.close) < float(bar.open):
                count += 1
            elif direction == "DOWN" and float(bar.close) > float(bar.open):
                count += 1
            else:
                if count:
                    break
        return count

    def _minor_trendline_break(self, candles, direction):
        sample = candles[-8:]
        if direction == "UP":
            lows = [float(x.low) for x in sample]
            return lows[-1] < min(lows[-4:-1])
        highs = [float(x.high) for x in sample]
        return highs[-1] > max(highs[-4:-1])

    def _moving_average_series(self, candles):
        values = []
        closes = [float(x.close) for x in candles]
        for i in range(len(closes)):
            start = max(0, i - self.MA_PERIOD + 1)
            window = closes[start:i + 1]
            values.append(sum(window) / len(window))
        return values

    def _moving_average_touch(self, candles, ma, direction):
        for i in range(max(1, len(candles) - 6), len(candles)):
            bar = candles[i]
            level = ma[i]
            if float(bar.low) <= level <= float(bar.high):
                return True
        return False

    def _moving_average_close_cross(self, candles, ma, direction):
        for i in range(max(1, len(candles) - 6), len(candles)):
            close = float(candles[i].close)
            if direction == "UP" and close < ma[i]:
                return True
            if direction == "DOWN" and close > ma[i]:
                return True
        return False

    def _moving_average_gap_bar(self, candles, ma, direction):
        for i in range(max(1, len(candles) - 6), len(candles)):
            bar = candles[i]
            level = ma[i]
            if direction == "UP" and float(bar.low) > level:
                return True
            if direction == "DOWN" and float(bar.high) < level:
                return True
        return False

    def _major_trendline_break(self, candles, direction):
        sample = candles[-12:]
        if len(sample) < 8:
            return False
        if direction == "UP":
            early_low = min(float(x.low) for x in sample[:6])
            late_low = min(float(x.low) for x in sample[6:])
            return late_low <= early_low
        early_high = max(float(x.high) for x in sample[:6])
        late_high = max(float(x.high) for x in sample[6:])
        return late_high >= early_high

    def _long_two_leg_pullback(self, candles, direction):
        sample = candles[-12:]
        if len(sample) < 10:
            return False
        counter = []
        for bar in sample:
            if direction == "UP":
                counter.append(float(bar.close) < float(bar.open))
            else:
                counter.append(float(bar.close) > float(bar.open))

        runs = 0
        in_run = False
        for value in counter:
            if value and not in_run:
                runs += 1
                in_run = True
            elif not value:
                in_run = False
        return runs >= 2 and sum(counter) >= 4

    def _two_sided_trading(self, candles):
        sample = candles[-10:]
        bulls = sum(float(x.close) > float(x.open) for x in sample)
        bears = sum(float(x.close) < float(x.open) for x in sample)
        overlap = 0
        for a, b in zip(sample, sample[1:]):
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlap += 1
        return bulls >= 3 and bears >= 3 and overlap >= 5

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
