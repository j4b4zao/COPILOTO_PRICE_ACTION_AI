"""
analysis/price_action/tight_trading_range_dynamics.py

Brooks Trading Ranges - Chapter 22:
Tight Trading Ranges.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TightTradingRangeResult:
    valid: bool = False
    state: str = "NONE"
    range_high: float = 0.0
    range_low: float = 0.0
    range_width: float = 0.0
    range_width_atr: float = 0.0
    overlap_ratio: float = 0.0
    doji_ratio: float = 0.0
    direction_changes: int = 0
    barbwire: bool = False
    no_trade_zone: bool = False
    breakout_attempt: bool = False
    breakout_confirmed: bool = False
    breakout_direction: str = "NONE"
    scalp_space_ok: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TightTradingRangeDynamics:
    """Detect tight ranges and mark environments where trading should be avoided."""

    MIN_HISTORY = 10
    LOOKBACK = 12
    TIGHT_WIDTH_ATR = 3.0
    VERY_TIGHT_WIDTH_ATR = 2.0
    MIN_OVERLAP_RATIO = 0.70
    BARBWIRE_DOJI_RATIO = 0.30
    BREAKOUT_BUFFER_ATR = 0.10

    def analyze(self, candles):
        # The last candle is assumed current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TightTradingRangeResult(reasons=("INSUFFICIENT_HISTORY",))

        sample = closed[-self.LOOKBACK:]
        atr = max(self._average_range(sample), 1e-9)

        range_high = max(float(x.high) for x in sample)
        range_low = min(float(x.low) for x in sample)
        width = max(range_high - range_low, 0.0)
        width_atr = width / atr

        overlap_ratio = self._overlap_ratio(sample)
        doji_ratio = self._doji_ratio(sample)
        direction_changes = self._direction_changes(sample)
        barbwire = (
            overlap_ratio >= self.MIN_OVERLAP_RATIO
            and doji_ratio >= self.BARBWIRE_DOJI_RATIO
            and direction_changes >= 4
        )

        breakout_attempt, breakout_confirmed, breakout_direction = (
            self._breakout_state(closed, sample, atr)
        )

        very_tight = (
            width_atr <= self.VERY_TIGHT_WIDTH_ATR
            and overlap_ratio >= self.MIN_OVERLAP_RATIO
        )
        tight = (
            width_atr <= self.TIGHT_WIDTH_ATR
            and overlap_ratio >= 0.60
        )

        scalp_space_ok = width_atr >= 2.5 and not barbwire

        if breakout_confirmed:
            state = "TIGHT_RANGE_BREAKOUT_CONFIRMED"
            no_trade_zone = False
        elif very_tight or barbwire:
            state = "NO_TRADE_ZONE"
            no_trade_zone = True
        elif tight:
            state = "TIGHT_TRADING_RANGE"
            no_trade_zone = True
        else:
            state = "NORMAL_RANGE_OR_OTHER"
            no_trade_zone = False

        reasons = [
            f"RANGE_WIDTH_ATR_{width_atr:.2f}",
            f"OVERLAP_{overlap_ratio:.2f}",
            f"DOJI_RATIO_{doji_ratio:.2f}",
            f"DIRECTION_CHANGES_{direction_changes}",
        ]
        if barbwire:
            reasons.append("BARBWIRE")
        if no_trade_zone:
            reasons.append("AVOID_TRADING_TIGHT_RANGE")
        if breakout_attempt:
            reasons.append(f"BREAKOUT_ATTEMPT_{breakout_direction}")
        if breakout_confirmed:
            reasons.append(f"BREAKOUT_CONFIRMED_{breakout_direction}")
        if not scalp_space_ok:
            reasons.append("INSUFFICIENT_SCALP_SPACE")

        return TightTradingRangeResult(
            valid=True,
            state=state,
            range_high=round(range_high, 6),
            range_low=round(range_low, 6),
            range_width=round(width, 6),
            range_width_atr=round(width_atr, 3),
            overlap_ratio=round(overlap_ratio, 3),
            doji_ratio=round(doji_ratio, 3),
            direction_changes=direction_changes,
            barbwire=barbwire,
            no_trade_zone=no_trade_zone,
            breakout_attempt=breakout_attempt,
            breakout_confirmed=breakout_confirmed,
            breakout_direction=breakout_direction,
            scalp_space_ok=scalp_space_ok,
            reasons=tuple(reasons),
        )

    def _breakout_state(self, closed, sample, atr):
        # Use the prior range only, then inspect the latest closed bars.
        if len(sample) < 6:
            return False, False, "NONE"

        base = sample[:-2]
        if len(base) < 4:
            return False, False, "NONE"

        high = max(float(x.high) for x in base)
        low = min(float(x.low) for x in base)
        b1 = sample[-2]
        b2 = sample[-1]
        buffer = atr * self.BREAKOUT_BUFFER_ATR

        if float(b1.close) > high + buffer:
            confirmed = (
                float(b2.close) > high
                and float(b2.low) >= high - buffer
            )
            return True, confirmed, "UP"

        if float(b1.close) < low - buffer:
            confirmed = (
                float(b2.close) < low
                and float(b2.high) <= low + buffer
            )
            return True, confirmed, "DOWN"

        return False, False, "NONE"

    @staticmethod
    def _average_range(candles):
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)

    @staticmethod
    def _overlap_ratio(candles):
        if len(candles) < 2:
            return 0.0
        overlaps = 0
        for a, b in zip(candles, candles[1:]):
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlaps += 1
        return overlaps / (len(candles) - 1)

    @staticmethod
    def _doji_ratio(candles):
        dojis = 0
        for bar in candles:
            rng = max(float(bar.high) - float(bar.low), 1e-9)
            body = abs(float(bar.close) - float(bar.open))
            if body / rng <= 0.25:
                dojis += 1
        return dojis / len(candles)

    @staticmethod
    def _direction_changes(candles):
        dirs = []
        for bar in candles:
            if float(bar.close) > float(bar.open):
                dirs.append(1)
            elif float(bar.close) < float(bar.open):
                dirs.append(-1)
            else:
                dirs.append(0)

        changes = 0
        prev = 0
        for d in dirs:
            if d == 0:
                continue
            if prev and d != prev:
                changes += 1
            prev = d
        return changes
