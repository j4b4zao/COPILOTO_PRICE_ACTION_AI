"""
analysis/price_action/climactic_reversal_dynamics.py

Brooks Reversals - Chapter 4:
Climactic Reversals: A Spike Followed by a Spike in the Opposite Direction.

Diagnostic-only layer. It detects exhaustion spikes and sharp opposite spikes
without mutating Score/Risk/Decision or sending orders.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ClimacticReversalResult:
    valid: bool = False
    old_trend: str = "NONE"
    reversal_direction: str = "NONE"
    state: str = "NO_CLIMAX"
    climax_detected: bool = False
    opposite_spike: bool = False
    failed_breakout: bool = False
    structural_break: bool = False
    follow_through: bool = False
    climax_range_ratio: float = 0.0
    opposite_range_ratio: float = 0.0
    quality_score: float = 0.0
    continuation_risk: bool = False
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ClimacticReversalDynamics:
    """Detect spike exhaustion followed by a sharp spike in the opposite direction."""

    MIN_HISTORY = 8
    LOOKBACK = 5
    CLIMAX_RANGE_MULT = 1.60
    STRONG_BODY_RATIO = 0.60
    STRONG_CLOSE_POS = 0.70

    def analyze(self, candles, old_trend, structural_break=False):
        old_trend = str(old_trend or "").upper()
        if old_trend not in ("UP", "DOWN"):
            return ClimacticReversalResult(
                reason="INVALID_OLD_TREND",
                reasons=("INVALID_OLD_TREND",),
            )

        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ClimacticReversalResult(
                old_trend=old_trend,
                reversal_direction="SELL" if old_trend == "UP" else "BUY",
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        reversal_direction = "SELL" if old_trend == "UP" else "BUY"
        climax_idx = self._find_recent_climax(closed, old_trend)
        if climax_idx is None:
            return ClimacticReversalResult(
                valid=True,
                old_trend=old_trend,
                reversal_direction=reversal_direction,
                state="NO_CLIMAX",
                continuation_risk=True,
                reason="NO_CLIMACTIC_SPIKE",
                reasons=("NO_CLIMACTIC_SPIKE",),
            )

        climax = closed[climax_idx]
        avg_range = self._avg_range(closed[max(0, climax_idx - self.LOOKBACK):climax_idx])
        climax_ratio = self._range(climax) / max(avg_range, 1e-9)

        after = closed[climax_idx + 1:]
        opposite_idx = None
        for i, candle in enumerate(after[:4]):
            if self._strong_directional(candle, reversal_direction):
                opposite_idx = climax_idx + 1 + i
                break

        opposite_spike = opposite_idx is not None
        opposite_ratio = 0.0
        follow_through = False
        failed_breakout = False
        reasons = ["CLIMACTIC_SPIKE_DETECTED"]

        if opposite_spike:
            opposite = closed[opposite_idx]
            opposite_ratio = self._range(opposite) / max(avg_range, 1e-9)
            reasons.append("OPPOSITE_SPIKE_DETECTED")

            # A sharp move back through the climax bar body is treated as a
            # failed breakout attempt in the original trend direction.
            if old_trend == "UP":
                failed_breakout = float(opposite.close) < float(climax.open)
            else:
                failed_breakout = float(opposite.close) > float(climax.open)

            if failed_breakout:
                reasons.append("ORIGINAL_BREAKOUT_FAILED")

            later = closed[opposite_idx + 1: opposite_idx + 3]
            follow_through = any(self._strong_directional(c, reversal_direction) for c in later)
            if follow_through:
                reasons.append("OPPOSITE_FOLLOW_THROUGH")

        if structural_break:
            reasons.append("STRUCTURAL_BREAK_CONFIRMED")

        score = 30.0
        if climax_ratio >= 2.0:
            score += 15.0
        elif climax_ratio >= self.CLIMAX_RANGE_MULT:
            score += 10.0
        if opposite_spike:
            score += 25.0
        if opposite_ratio >= 1.30:
            score += 10.0
        if failed_breakout:
            score += 10.0
        if structural_break:
            score += 10.0
        if follow_through:
            score += 15.0
        score = min(score, 100.0)

        confirmed = opposite_spike and failed_breakout and follow_through
        if confirmed:
            state = "CLIMACTIC_REVERSAL_CONFIRMED"
            continuation_risk = False
        elif opposite_spike:
            state = "OPPOSITE_SPIKE_WAIT"
            continuation_risk = True
        else:
            state = "CLIMAX_PAUSE_WAIT"
            continuation_risk = True

        return ClimacticReversalResult(
            valid=True,
            old_trend=old_trend,
            reversal_direction=reversal_direction,
            state=state,
            climax_detected=True,
            opposite_spike=opposite_spike,
            failed_breakout=failed_breakout,
            structural_break=bool(structural_break),
            follow_through=follow_through,
            climax_range_ratio=round(climax_ratio, 2),
            opposite_range_ratio=round(opposite_ratio, 2),
            quality_score=round(score, 1),
            continuation_risk=continuation_risk,
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    def _find_recent_climax(self, candles, old_trend):
        start = max(self.LOOKBACK, len(candles) - 7)
        for idx in range(start, len(candles)):
            prior = candles[max(0, idx - self.LOOKBACK):idx]
            avg_range = self._avg_range(prior)
            if avg_range <= 0:
                continue
            candle = candles[idx]
            if (
                self._range(candle) >= avg_range * self.CLIMAX_RANGE_MULT
                and self._strong_directional(candle, "BUY" if old_trend == "UP" else "SELL")
            ):
                return idx
        return None

    @staticmethod
    def _range(candle):
        return max(float(candle.high) - float(candle.low), 0.0)

    def _avg_range(self, candles):
        if not candles:
            return 0.0
        return sum(self._range(c) for c in candles) / len(candles)

    def _strong_directional(self, candle, direction):
        high = float(candle.high)
        low = float(candle.low)
        open_ = float(candle.open)
        close = float(candle.close)
        rng = max(high - low, 1e-9)
        body_ratio = abs(close - open_) / rng

        if direction == "BUY":
            close_pos = (close - low) / rng
            directional = close > open_
        else:
            close_pos = (high - close) / rng
            directional = close < open_

        return (
            directional
            and body_ratio >= self.STRONG_BODY_RATIO
            and close_pos >= self.STRONG_CLOSE_POS
        )
