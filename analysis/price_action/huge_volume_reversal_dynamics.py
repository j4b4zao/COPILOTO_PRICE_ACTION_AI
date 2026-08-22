"""
analysis/price_action/huge_volume_reversal_dynamics.py

Brooks Reversals - Chapter 10:
Huge Volume Reversals on Daily Charts.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class HugeVolumeReversalResult:
    valid: bool = False
    timeframe: str = "UNKNOWN"
    canonical_daily_context: bool = False
    old_trend: str = "NONE"
    reversal_direction: str = "NONE"
    pattern: str = "NO_HUGE_VOLUME_REVERSAL"
    huge_volume: bool = False
    volume_ratio: float = 0.0
    extended_move: bool = False
    climactic_bar: bool = False
    rejection: bool = False
    opposite_response: bool = False
    follow_through: bool = False
    reversal_confirmed: bool = False
    continuation_risk: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class HugeVolumeReversalDynamics:
    """Detect abnormal-volume exhaustion followed by confirmed reversal pressure."""

    MIN_HISTORY = 14
    BASELINE = 10
    HUGE_VOLUME_RATIO = 2.0
    EXTENSION_ATR = 2.0

    def analyze(self, candles, timeframe="D1"):
        closed = list(candles[:-1]) if candles else []
        tf = str(timeframe or "UNKNOWN").upper()
        daily = tf in {"D", "D1", "1D", "DAILY"}

        if len(closed) < self.MIN_HISTORY:
            return HugeVolumeReversalResult(
                timeframe=tf,
                canonical_daily_context=daily,
                reasons=("INSUFFICIENT_HISTORY",),
            )

        candidate_index = self._find_huge_volume_bar(closed)
        if candidate_index is None:
            return HugeVolumeReversalResult(
                timeframe=tf,
                canonical_daily_context=daily,
                reasons=("NO_HUGE_VOLUME_BAR",),
            )

        candidate = closed[candidate_index]
        baseline_start = max(0, candidate_index - self.BASELINE)
        baseline = closed[baseline_start:candidate_index]
        avg_volume = self._average_volume(baseline)
        volume_ratio = self._volume(candidate) / max(avg_volume, 1e-9)

        old_trend = self._infer_old_trend(closed[:candidate_index + 1])
        if old_trend == "NONE":
            return HugeVolumeReversalResult(
                valid=True,
                timeframe=tf,
                canonical_daily_context=daily,
                huge_volume=True,
                volume_ratio=round(volume_ratio, 2),
                reasons=("HUGE_VOLUME_WITHOUT_CLEAR_PRIOR_TREND",),
            )

        reversal_direction = "SELL" if old_trend == "UP" else "BUY"
        extended = self._extended_move(closed[:candidate_index + 1], old_trend)
        climactic = self._climactic(candidate, closed[max(0, candidate_index - 8):candidate_index])
        rejection = self._rejection(candidate, old_trend)

        after = closed[candidate_index + 1:]
        opposite_response = self._opposite_response(after, reversal_direction)
        follow_through = self._follow_through(after, reversal_direction)
        confirmed = (
            volume_ratio >= self.HUGE_VOLUME_RATIO
            and extended
            and (climactic or rejection)
            and opposite_response
            and follow_through
        )

        if confirmed:
            pattern = "HUGE_VOLUME_REVERSAL_CONFIRMED"
        elif opposite_response:
            pattern = "HUGE_VOLUME_REVERSAL_WAIT_FOLLOW_THROUGH"
        else:
            pattern = "HUGE_VOLUME_EXHAUSTION_WATCH"

        score = 0.0
        score += min(30.0, max(0.0, (volume_ratio - 1.0) * 20.0))
        score += 20.0 if extended else 0.0
        score += 15.0 if climactic else 0.0
        score += 10.0 if rejection else 0.0
        score += 10.0 if opposite_response else 0.0
        score += 15.0 if follow_through else 0.0

        reasons = ["HUGE_VOLUME"]
        if daily:
            reasons.append("DAILY_CHART_CANONICAL_CONTEXT")
        if extended:
            reasons.append("EXTENDED_PRIOR_MOVE")
        if climactic:
            reasons.append("CLIMACTIC_RANGE")
        if rejection:
            reasons.append("EXTREME_REJECTION")
        if opposite_response:
            reasons.append("OPPOSITE_RESPONSE")
        if follow_through:
            reasons.append("OPPOSITE_FOLLOW_THROUGH")
        if not confirmed:
            reasons.append("VOLUME_ALONE_NOT_REVERSAL")

        return HugeVolumeReversalResult(
            valid=True,
            timeframe=tf,
            canonical_daily_context=daily,
            old_trend=old_trend,
            reversal_direction=reversal_direction,
            pattern=pattern,
            huge_volume=True,
            volume_ratio=round(volume_ratio, 2),
            extended_move=extended,
            climactic_bar=climactic,
            rejection=rejection,
            opposite_response=opposite_response,
            follow_through=follow_through,
            reversal_confirmed=confirmed,
            continuation_risk=not confirmed,
            quality_score=round(min(score, 100.0), 1),
            reasons=tuple(reasons),
        )

    def _find_huge_volume_bar(self, candles):
        start = max(self.BASELINE, len(candles) - 5)
        for i in range(len(candles) - 1, start - 1, -1):
            baseline = candles[max(0, i - self.BASELINE):i]
            if len(baseline) < 5:
                continue
            avg = self._average_volume(baseline)
            if avg > 0 and self._volume(candles[i]) >= avg * self.HUGE_VOLUME_RATIO:
                return i
        return None

    def _infer_old_trend(self, candles):
        if len(candles) < 8:
            return "NONE"
        sample = candles[-8:]
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        if delta >= atr * 1.5:
            return "UP"
        if delta <= -atr * 1.5:
            return "DOWN"
        return "NONE"

    def _extended_move(self, candles, trend):
        sample = candles[-10:]
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        return delta >= atr * self.EXTENSION_ATR if trend == "UP" else delta <= -atr * self.EXTENSION_ATR

    def _climactic(self, bar, baseline):
        avg_range = max(self._average_range(baseline), 1e-9)
        return self._range(bar) >= avg_range * 1.6

    @staticmethod
    def _rejection(bar, old_trend):
        high = float(bar.high)
        low = float(bar.low)
        open_ = float(bar.open)
        close = float(bar.close)
        total = max(high - low, 1e-9)
        if old_trend == "UP":
            upper_tail = high - max(open_, close)
            return upper_tail / total >= 0.30 or close < open_
        lower_tail = min(open_, close) - low
        return lower_tail / total >= 0.30 or close > open_

    @staticmethod
    def _opposite_response(after, direction):
        if not after:
            return False
        for bar in after[:2]:
            if direction == "SELL" and float(bar.close) < float(bar.open):
                return True
            if direction == "BUY" and float(bar.close) > float(bar.open):
                return True
        return False

    @staticmethod
    def _follow_through(after, direction):
        if len(after) < 2:
            return False
        a, b = after[0], after[1]
        if direction == "SELL":
            return float(a.close) < float(a.open) and float(b.close) < float(a.low)
        return float(a.close) > float(a.open) and float(b.close) > float(a.high)

    @staticmethod
    def _volume(bar):
        return float(getattr(bar, "volume", 0.0) or 0.0)

    @staticmethod
    def _range(bar):
        return max(float(bar.high) - float(bar.low), 0.0)

    def _average_volume(self, candles):
        if not candles:
            return 0.0
        return sum(self._volume(x) for x in candles) / len(candles)

    def _average_range(self, candles):
        if not candles:
            return 0.0
        return sum(self._range(x) for x in candles) / len(candles)
