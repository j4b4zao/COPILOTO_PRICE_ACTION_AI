"""
analysis/price_action/bar_count_dynamics.py

Brooks Trading Ranges - Chapter 17:
Bar counting: High/Low 1, 2, 3, 4 patterns and ABC corrections.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class BarCountResult:
    valid: bool = False
    trend_direction: str = "NONE"
    setup_direction: str = "NONE"
    pattern: str = "NONE"
    attempt_count: int = 0
    pullback_start_index: int = -1
    signal_bar_index: int = -1
    abc_correction: bool = False
    two_leg_pullback: bool = False
    first_attempt_failed: bool = False
    signal_confirmed: bool = False
    continuation_bias: bool = False
    exhaustion_risk: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class BarCountDynamics:
    """Count Brooks H1-H4 / L1-L4 attempts during trend pullbacks."""

    MIN_HISTORY = 12
    LOOKBACK = 24
    MAX_ATTEMPTS = 4

    def analyze(self, candles):
        # Last candle is current/forming and must not confirm a setup.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return BarCountResult(reasons=("INSUFFICIENT_HISTORY",))

        trend = self._infer_trend(closed)
        if trend == "NONE":
            return BarCountResult(reasons=("NO_CLEAR_TREND",))

        start = self._find_pullback_start(closed, trend)
        if start is None:
            return BarCountResult(
                trend_direction=trend,
                reasons=("NO_ACTIVE_PULLBACK",),
            )

        attempts = self._count_attempts(closed, start, trend)
        if not attempts:
            return BarCountResult(
                trend_direction=trend,
                pullback_start_index=start,
                reasons=("PULLBACK_WITHOUT_RESUMPTION_ATTEMPT",),
            )

        attempt_count = min(len(attempts), self.MAX_ATTEMPTS)
        signal_idx = attempts[-1]
        prefix = "HIGH" if trend == "UP" else "LOW"
        pattern = f"{prefix}_{attempt_count}" if attempt_count < 4 else f"{prefix}_4"

        first_failed = self._attempt_failed(closed, attempts[0], trend) if len(attempts) >= 2 else False
        two_leg = self._has_two_counter_legs(closed, start, signal_idx, trend)
        abc = two_leg and attempt_count >= 2
        confirmed = self._confirmed_after_signal(closed, signal_idx, trend)
        continuation_bias = confirmed and attempt_count in (1, 2)
        exhaustion_risk = attempt_count >= 3

        reasons = [
            f"TREND_{trend}",
            pattern,
        ]
        if first_failed:
            reasons.append("FIRST_ATTEMPT_FAILED")
        if two_leg:
            reasons.append("TWO_LEG_PULLBACK")
        if abc:
            reasons.append("ABC_CORRECTION")
        if confirmed:
            reasons.append("RESUMPTION_CONFIRMED")
        else:
            reasons.append("WAIT_CONFIRMATION")
        if exhaustion_risk:
            reasons.append("LATE_ATTEMPT_EXHAUSTION_RISK")

        return BarCountResult(
            valid=True,
            trend_direction=trend,
            setup_direction="BUY" if trend == "UP" else "SELL",
            pattern=pattern,
            attempt_count=attempt_count,
            pullback_start_index=start,
            signal_bar_index=signal_idx,
            abc_correction=abc,
            two_leg_pullback=two_leg,
            first_attempt_failed=first_failed,
            signal_confirmed=confirmed,
            continuation_bias=continuation_bias,
            exhaustion_risk=exhaustion_risk,
            reasons=tuple(reasons),
        )

    def _infer_trend(self, candles):
        sample = candles[-10:]
        if len(sample) < 8:
            return "NONE"
        atr = max(self._average_range(sample), 1e-9)
        delta = float(sample[-1].close) - float(sample[0].close)
        if delta >= atr * 1.5:
            return "UP"
        if delta <= -atr * 1.5:
            return "DOWN"

        highs = [float(x.high) for x in sample]
        lows = [float(x.low) for x in sample]
        if max(highs[-4:]) > max(highs[:4]) and min(lows[-4:]) > min(lows[:4]):
            return "UP"
        if max(highs[-4:]) < max(highs[:4]) and min(lows[-4:]) < min(lows[:4]):
            return "DOWN"
        return "NONE"

    def _find_pullback_start(self, candles, trend):
        start = max(2, len(candles) - self.LOOKBACK)
        # Work forward from a recent trend extreme and choose the latest
        # counter-trend sequence that still belongs to the current trend.
        for i in range(len(candles) - 3, start - 1, -1):
            bar = candles[i]
            prev = candles[i - 1]
            if trend == "UP":
                if float(bar.low) < float(prev.low) or float(bar.close) < float(bar.open):
                    return i
            else:
                if float(bar.high) > float(prev.high) or float(bar.close) > float(bar.open):
                    return i
        return None

    def _count_attempts(self, candles, start, trend):
        attempts = []
        armed = True
        for i in range(start + 1, len(candles)):
            prev = candles[i - 1]
            bar = candles[i]
            if trend == "UP":
                trigger = float(bar.high) > float(prev.high)
                counter_reset = float(bar.low) < float(prev.low)
            else:
                trigger = float(bar.low) < float(prev.low)
                counter_reset = float(bar.high) > float(prev.high)

            if trigger and armed:
                attempts.append(i)
                armed = False
                if len(attempts) >= self.MAX_ATTEMPTS:
                    break
            elif counter_reset:
                armed = True

        return attempts

    def _attempt_failed(self, candles, idx, trend):
        if idx + 1 >= len(candles):
            return False
        signal = candles[idx]
        after = candles[idx + 1]
        if trend == "UP":
            return float(after.low) < float(signal.low)
        return float(after.high) > float(signal.high)

    def _has_two_counter_legs(self, candles, start, end, trend):
        if end - start < 3:
            return False
        counter_runs = 0
        in_counter = False
        for bar in candles[start:end + 1]:
            counter = (
                float(bar.close) < float(bar.open)
                if trend == "UP"
                else float(bar.close) > float(bar.open)
            )
            if counter and not in_counter:
                counter_runs += 1
                in_counter = True
            elif not counter:
                in_counter = False
        return counter_runs >= 2

    def _confirmed_after_signal(self, candles, idx, trend):
        if idx + 1 >= len(candles):
            return False
        signal = candles[idx]
        follow = candles[idx + 1]
        if trend == "UP":
            return (
                float(follow.close) > float(signal.high)
                or (
                    float(follow.close) > float(follow.open)
                    and float(follow.close) > float(signal.close)
                )
            )
        return (
            float(follow.close) < float(signal.low)
            or (
                float(follow.close) < float(follow.open)
                and float(follow.close) < float(signal.close)
            )
        )

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
