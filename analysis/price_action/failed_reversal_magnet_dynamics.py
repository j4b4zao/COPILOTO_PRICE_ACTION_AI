"""
analysis/price_action/failed_reversal_magnet_dynamics.py

Brooks Trading Ranges - Chapter 9:
Reversals often end at prior failed reversal signal bars.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class FailedReversalMagnetResult:
    valid: bool = False
    trend_direction: str = "NONE"
    magnet_direction: str = "NONE"
    magnet_price: float = 0.0
    signal_bar_index: int = -1
    signal_type: str = "NONE"
    state: str = "NO_MAGNET"
    distance: float = 0.0
    distance_ratio: float = 0.0
    touched: bool = False
    rejected: bool = False
    crossed: bool = False
    magnet_active: bool = False
    support_resistance_role: str = "NONE"
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class FailedReversalMagnetDynamics:
    """Track failed reversal signal bars that can later act as price magnets."""

    MIN_HISTORY = 10
    LOOKBACK = 30
    TOUCH_TOLERANCE_RATIO = 0.15
    APPROACH_TOLERANCE_RATIO = 0.75

    def analyze(self, candles):
        # Last candle is assumed to be current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return FailedReversalMagnetResult(
                reasons=("INSUFFICIENT_HISTORY",),
            )

        trend = self._infer_trend(closed)
        if trend == "NONE":
            return FailedReversalMagnetResult(
                reasons=("NO_CLEAR_TREND",),
            )

        candidate = self._find_failed_reversal_signal(closed, trend)
        if candidate is None:
            return FailedReversalMagnetResult(
                trend_direction=trend,
                reasons=("NO_FAILED_REVERSAL_SIGNAL",),
            )

        idx, signal_type, magnet_price, role = candidate
        current = closed[-1]
        atr = self._average_range(closed[-10:])
        atr = max(atr, 1e-9)

        if trend == "DOWN":
            distance = max(float(current.close) - magnet_price, 0.0)
            touched = float(current.low) <= magnet_price <= float(current.high)
            crossed = float(current.close) < magnet_price
            rejected = touched and float(current.close) > magnet_price
            magnet_direction = "DOWN"
        else:
            distance = max(magnet_price - float(current.close), 0.0)
            touched = float(current.low) <= magnet_price <= float(current.high)
            crossed = float(current.close) > magnet_price
            rejected = touched and float(current.close) < magnet_price
            magnet_direction = "UP"

        distance_ratio = distance / atr

        if crossed:
            state = "MAGNET_CROSSED"
        elif rejected:
            state = "MAGNET_REJECTED"
        elif touched:
            state = "MAGNET_TESTED"
        elif distance_ratio <= self.APPROACH_TOLERANCE_RATIO:
            state = "APPROACHING_MAGNET"
        else:
            state = "MAGNET_ACTIVE"

        reasons = [
            "FAILED_REVERSAL_SIGNAL_BAR",
            f"TREND_{trend}",
        ]
        if touched:
            reasons.append("MAGNET_TESTED")
        if rejected:
            reasons.append("REACTION_AT_MAGNET")
        if crossed:
            reasons.append("MAGNET_CROSSED")

        return FailedReversalMagnetResult(
            valid=True,
            trend_direction=trend,
            magnet_direction=magnet_direction,
            magnet_price=magnet_price,
            signal_bar_index=idx,
            signal_type=signal_type,
            state=state,
            distance=distance,
            distance_ratio=distance_ratio,
            touched=touched,
            rejected=rejected,
            crossed=crossed,
            magnet_active=not crossed,
            support_resistance_role=role,
            reasons=tuple(reasons),
        )

    def _infer_trend(self, candles):
        sample = candles[-8:]
        if len(sample) < 6:
            return "NONE"

        closes = [float(x.close) for x in sample]
        rise = closes[-1] - closes[0]
        avg_range = self._average_range(sample)

        if rise >= avg_range * 1.5:
            return "UP"
        if rise <= -avg_range * 1.5:
            return "DOWN"
        return "NONE"

    def _find_failed_reversal_signal(self, candles, trend):
        start = max(2, len(candles) - self.LOOKBACK)
        end = len(candles) - 3

        for idx in range(end, start - 1, -1):
            bar = candles[idx]
            prev = candles[idx - 1]
            after = candles[idx + 1 : idx + 3]
            bar_range = max(float(bar.high) - float(bar.low), 1e-9)
            body = abs(float(bar.close) - float(bar.open))
            body_ratio = body / bar_range

            if trend == "DOWN":
                # Failed bullish reversal inside a bear trend. The high of the
                # bullish signal bar becomes a future magnet for rallies.
                bullish_signal = (
                    float(bar.close) > float(bar.open)
                    and float(bar.low) <= float(prev.low)
                    and body_ratio >= 0.35
                )
                failure = (
                    bullish_signal
                    and all(float(x.close) < float(bar.high) for x in after)
                    and any(float(x.close) < float(bar.low) for x in after)
                )
                if failure:
                    return idx, "FAILED_BULL_REVERSAL", float(bar.high), "RESISTANCE"

            else:
                # Failed bearish reversal inside a bull trend. The low of the
                # bearish signal bar becomes a future magnet for selloffs.
                bearish_signal = (
                    float(bar.close) < float(bar.open)
                    and float(bar.high) >= float(prev.high)
                    and body_ratio >= 0.35
                )
                failure = (
                    bearish_signal
                    and all(float(x.close) > float(bar.low) for x in after)
                    and any(float(x.close) > float(bar.high) for x in after)
                )
                if failure:
                    return idx, "FAILED_BEAR_REVERSAL", float(bar.low), "SUPPORT"

        return None

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
