"""
analysis/price_action/trading_range_playbook_dynamics.py

Brooks Trading Ranges - Chapter 21:
Example of how to trade a trading range.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TradingRangePlaybookResult:
    valid: bool = False
    state: str = "NO_RANGE"
    range_low: float = 0.0
    range_high: float = 0.0
    range_mid: float = 0.0
    range_height: float = 0.0
    position: float = 0.5
    zone: str = "MIDDLE"
    setup_direction: str = "NONE"
    h2_near_low: bool = False
    l2_near_high: bool = False
    breakout_attempt: bool = False
    failed_breakout_risk: bool = False
    scalp_bias: bool = False
    avoid_middle: bool = False
    swing_candidate: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TradingRangePlaybookDynamics:
    """Classify location and Brooks-style tactics inside a trading range."""

    MIN_HISTORY = 14
    LOOKBACK = 18
    EDGE_FRACTION = 0.30
    MAX_TREND_EFFICIENCY = 0.42

    def analyze(self, candles):
        # Last candle is assumed current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TradingRangePlaybookResult(reasons=("INSUFFICIENT_HISTORY",))

        sample = closed[-self.LOOKBACK:]
        low = min(float(x.low) for x in sample)
        high = max(float(x.high) for x in sample)
        height = high - low
        if height <= 0:
            return TradingRangePlaybookResult(reasons=("INVALID_RANGE",))

        efficiency = self._directional_efficiency(sample)
        overlap_ratio = self._overlap_ratio(sample)
        two_sided = self._two_sided(sample)

        if efficiency > self.MAX_TREND_EFFICIENCY or overlap_ratio < 0.45 or not two_sided:
            return TradingRangePlaybookResult(
                range_low=low,
                range_high=high,
                range_mid=(low + high) / 2.0,
                range_height=height,
                reasons=("NO_STABLE_TRADING_RANGE",),
            )

        last = sample[-1]
        price = float(last.close)
        position = min(max((price - low) / height, 0.0), 1.0)
        zone = self._zone(position)

        h2 = zone == "LOW" and self._high2(sample)
        l2 = zone == "HIGH" and self._low2(sample)
        breakout_attempt, failed_breakout = self._breakout_attempt(sample, low, high, height)

        setup_direction = "NONE"
        if h2:
            setup_direction = "BUY"
        elif l2:
            setup_direction = "SELL"

        avoid_middle = zone == "MIDDLE"
        scalp_bias = zone in ("LOW", "HIGH") and not breakout_attempt
        swing_candidate = height >= self._average_range(sample) * 4.0

        state = "RANGE_MIDDLE_AVOID"
        if h2:
            state = "BUY_LOW_H2"
        elif l2:
            state = "SELL_HIGH_L2"
        elif breakout_attempt:
            state = "BREAKOUT_ATTEMPT"
        elif zone == "LOW":
            state = "BUY_LOW_WATCH"
        elif zone == "HIGH":
            state = "SELL_HIGH_WATCH"

        reasons = [
            "TRADING_RANGE_CONFIRMED",
            f"ZONE_{zone}",
            f"OVERLAP_{overlap_ratio:.2f}",
            f"EFFICIENCY_{efficiency:.2f}",
        ]
        if h2:
            reasons.append("HIGH_2_NEAR_RANGE_LOW")
        if l2:
            reasons.append("LOW_2_NEAR_RANGE_HIGH")
        if breakout_attempt:
            reasons.append("BREAKOUT_ATTEMPT")
        if failed_breakout:
            reasons.append("FAILED_BREAKOUT_RISK")
        if avoid_middle:
            reasons.append("AVOID_MIDDLE")
        if scalp_bias:
            reasons.append("SCALP_ORIENTED")

        return TradingRangePlaybookResult(
            valid=True,
            state=state,
            range_low=round(low, 6),
            range_high=round(high, 6),
            range_mid=round((low + high) / 2.0, 6),
            range_height=round(height, 6),
            position=round(position, 3),
            zone=zone,
            setup_direction=setup_direction,
            h2_near_low=h2,
            l2_near_high=l2,
            breakout_attempt=breakout_attempt,
            failed_breakout_risk=failed_breakout,
            scalp_bias=scalp_bias,
            avoid_middle=avoid_middle,
            swing_candidate=swing_candidate,
            reasons=tuple(reasons),
        )

    def _zone(self, position):
        if position <= self.EDGE_FRACTION:
            return "LOW"
        if position >= 1.0 - self.EDGE_FRACTION:
            return "HIGH"
        return "MIDDLE"

    @staticmethod
    def _directional_efficiency(candles):
        total = sum(abs(float(b.close) - float(a.close)) for a, b in zip(candles, candles[1:]))
        if total <= 1e-9:
            return 0.0
        net = abs(float(candles[-1].close) - float(candles[0].close))
        return net / total

    @staticmethod
    def _overlap_ratio(candles):
        pairs = list(zip(candles, candles[1:]))
        if not pairs:
            return 0.0
        overlap = 0
        for a, b in pairs:
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlap += 1
        return overlap / len(pairs)

    @staticmethod
    def _two_sided(candles):
        bulls = sum(float(x.close) > float(x.open) for x in candles)
        bears = sum(float(x.close) < float(x.open) for x in candles)
        return bulls >= 3 and bears >= 3

    @staticmethod
    def _high2(candles):
        if len(candles) < 6:
            return False
        attempts = 0
        armed = True
        for i in range(max(1, len(candles) - 8), len(candles)):
            prev, bar = candles[i - 1], candles[i]
            if float(bar.high) > float(prev.high) and armed:
                attempts += 1
                armed = False
            elif float(bar.low) < float(prev.low):
                armed = True
        return attempts >= 2

    @staticmethod
    def _low2(candles):
        if len(candles) < 6:
            return False
        attempts = 0
        armed = True
        for i in range(max(1, len(candles) - 8), len(candles)):
            prev, bar = candles[i - 1], candles[i]
            if float(bar.low) < float(prev.low) and armed:
                attempts += 1
                armed = False
            elif float(bar.high) > float(prev.high):
                armed = True
        return attempts >= 2

    def _breakout_attempt(self, candles, low, high, height):
        if len(candles) < 3:
            return False, False
        prior = candles[-2]
        last = candles[-1]
        tol = height * 0.05
        up = float(prior.high) > high - tol and float(last.high) >= high
        down = float(prior.low) < low + tol and float(last.low) <= low
        attempt = up or down
        failed = False
        if up:
            failed = float(last.close) < high
        elif down:
            failed = float(last.close) > low
        return attempt, failed

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(x.high) - float(x.low), 0.0) for x in candles) / len(candles)
