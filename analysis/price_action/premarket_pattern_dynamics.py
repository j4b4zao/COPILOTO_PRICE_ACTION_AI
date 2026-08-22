"""
analysis/price_action/premarket_pattern_dynamics.py

Brooks Reversals - Chapter 17: Premarket-related patterns.
Diagnostic-only layer for opening-range behavior tied to premarket levels.

The module keeps premarket information as context, not as an automatic signal.
It excludes the current/incomplete candle from confirmation logic.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class PremarketPatternResult:
    valid: bool = False
    status: str = "UNKNOWN"
    premarket_high: float = 0.0
    premarket_low: float = 0.0
    premarket_open: float = 0.0
    premarket_close: float = 0.0
    premarket_direction: str = "NONE"
    regular_open: float = 0.0
    gap_direction: str = "NONE"
    gap_size: float = 0.0
    high_tested: bool = False
    low_tested: bool = False
    high_rejected: bool = False
    low_rejected: bool = False
    high_breakout_confirmed: bool = False
    low_breakout_confirmed: bool = False
    gap_closing_momentum: bool = False
    moving_average_conflict: bool = False
    momentum_over_ma: bool = False
    pattern_completed_after_open: bool = False
    reversal_watch: bool = False
    breakout_watch: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class PremarketPatternDynamics:
    """Evaluate premarket levels and their completion during the first hour."""

    MIN_PREMARKET_BARS = 4
    MIN_REGULAR_BARS = 3

    def analyze(
        self,
        premarket_candles,
        regular_candles,
        *,
        regular_ma=None,
        extended_ma=None,
        touch_tolerance=0.0015,
    ):
        pm = list(premarket_candles or [])
        rg = list(regular_candles or [])

        # Current/incomplete bars are excluded on both series.
        pm_closed = pm[:-1] if pm else []
        rg_closed = rg[:-1] if rg else []

        if len(pm_closed) < self.MIN_PREMARKET_BARS or len(rg_closed) < self.MIN_REGULAR_BARS:
            return PremarketPatternResult(reasons=("INSUFFICIENT_HISTORY",))

        pm_high = max(float(c.high) for c in pm_closed)
        pm_low = min(float(c.low) for c in pm_closed)
        pm_open = float(pm_closed[0].open)
        pm_close = float(pm_closed[-1].close)
        regular_open = float(rg_closed[0].open)

        pm_direction = self._direction(pm_open, pm_close)

        if regular_open > pm_high:
            gap_direction = "UP"
            gap_size = regular_open - pm_high
        elif regular_open < pm_low:
            gap_direction = "DOWN"
            gap_size = pm_low - regular_open
        else:
            gap_direction = "INSIDE"
            gap_size = 0.0

        pm_range = max(pm_high - pm_low, 1e-9)
        tol = max(pm_range * float(touch_tolerance), 1e-9)

        high_tested = any(float(c.high) >= pm_high - tol for c in rg_closed)
        low_tested = any(float(c.low) <= pm_low + tol for c in rg_closed)

        high_rejected = any(
            float(c.high) > pm_high and float(c.close) < pm_high
            for c in rg_closed
        )
        low_rejected = any(
            float(c.low) < pm_low and float(c.close) > pm_low
            for c in rg_closed
        )

        high_breakout_confirmed = self._confirmed_breakout(rg_closed, pm_high, "UP")
        low_breakout_confirmed = self._confirmed_breakout(rg_closed, pm_low, "DOWN")

        gap_closing_momentum = False
        if gap_direction == "DOWN":
            gap_closing_momentum = self._momentum(rg_closed, "UP")
        elif gap_direction == "UP":
            gap_closing_momentum = self._momentum(rg_closed, "DOWN")

        ma_conflict = False
        momentum_over_ma = False
        if regular_ma is not None and extended_ma is not None:
            regular_ma = float(regular_ma)
            extended_ma = float(extended_ma)
            ma_conflict = (regular_ma - extended_ma) * (pm_close - regular_open) < 0
            momentum_over_ma = ma_conflict and gap_closing_momentum

        pattern_completed = (
            high_rejected
            or low_rejected
            or high_breakout_confirmed
            or low_breakout_confirmed
        )

        reversal_watch = high_rejected or low_rejected
        breakout_watch = high_breakout_confirmed or low_breakout_confirmed

        score = 25.0
        if high_tested or low_tested:
            score += 15.0
        if pattern_completed:
            score += 25.0
        if gap_closing_momentum:
            score += 20.0
        if momentum_over_ma:
            score += 15.0
        score = min(score, 100.0)

        if high_breakout_confirmed:
            status = "PREMARKET_HIGH_BREAKOUT_CONFIRMED"
        elif low_breakout_confirmed:
            status = "PREMARKET_LOW_BREAKOUT_CONFIRMED"
        elif high_rejected:
            status = "PREMARKET_HIGH_REJECTION"
        elif low_rejected:
            status = "PREMARKET_LOW_REJECTION"
        elif high_tested or low_tested:
            status = "PREMARKET_LEVEL_TEST"
        elif gap_closing_momentum:
            status = "PREMARKET_GAP_CLOSE_MOMENTUM"
        else:
            status = "PREMARKET_CONTEXT_READY"

        reasons = [
            f"PREMARKET_DIRECTION_{pm_direction}",
            f"GAP_{gap_direction}",
        ]
        if high_tested:
            reasons.append("PREMARKET_HIGH_TESTED")
        if low_tested:
            reasons.append("PREMARKET_LOW_TESTED")
        if high_rejected:
            reasons.append("FAILED_BREAKOUT_ABOVE_PREMARKET_HIGH")
        if low_rejected:
            reasons.append("FAILED_BREAKOUT_BELOW_PREMARKET_LOW")
        if high_breakout_confirmed:
            reasons.append("BREAKOUT_ABOVE_PREMARKET_HIGH_WITH_FOLLOW_THROUGH")
        if low_breakout_confirmed:
            reasons.append("BREAKOUT_BELOW_PREMARKET_LOW_WITH_FOLLOW_THROUGH")
        if gap_closing_momentum:
            reasons.append("MOMENTUM_CLOSING_OPENING_GAP")
        if ma_conflict:
            reasons.append("REGULAR_AND_EXTENDED_SESSION_MA_CONFLICT")
        if momentum_over_ma:
            reasons.append("FIRST_HOUR_MOMENTUM_WEIGHTED_OVER_MA_CONFLICT")

        return PremarketPatternResult(
            valid=True,
            status=status,
            premarket_high=pm_high,
            premarket_low=pm_low,
            premarket_open=pm_open,
            premarket_close=pm_close,
            premarket_direction=pm_direction,
            regular_open=regular_open,
            gap_direction=gap_direction,
            gap_size=round(gap_size, 6),
            high_tested=high_tested,
            low_tested=low_tested,
            high_rejected=high_rejected,
            low_rejected=low_rejected,
            high_breakout_confirmed=high_breakout_confirmed,
            low_breakout_confirmed=low_breakout_confirmed,
            gap_closing_momentum=gap_closing_momentum,
            moving_average_conflict=ma_conflict,
            momentum_over_ma=momentum_over_ma,
            pattern_completed_after_open=pattern_completed,
            reversal_watch=reversal_watch,
            breakout_watch=breakout_watch,
            quality_score=round(score, 1),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _direction(open_price, close_price):
        if close_price > open_price:
            return "UP"
        if close_price < open_price:
            return "DOWN"
        return "FLAT"

    @staticmethod
    def _momentum(candles, direction):
        recent = candles[-3:]
        if len(recent) < 2:
            return False

        if direction == "UP":
            directional = [c for c in recent if float(c.close) > float(c.open)]
            return len(directional) >= 2 and float(recent[-1].close) > float(recent[0].close)

        directional = [c for c in recent if float(c.close) < float(c.open)]
        return len(directional) >= 2 and float(recent[-1].close) < float(recent[0].close)

    @staticmethod
    def _confirmed_breakout(candles, level, direction):
        if len(candles) < 2:
            return False

        for first, second in zip(candles[:-1], candles[1:]):
            if direction == "UP":
                if float(first.close) > level and float(second.close) > level:
                    return True
            else:
                if float(first.close) < level and float(second.close) < level:
                    return True
        return False
