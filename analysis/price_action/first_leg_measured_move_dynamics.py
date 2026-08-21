"""
analysis/price_action/first_leg_measured_move_dynamics.py

Brooks Trading Ranges - Chapter 7: Measured Moves based on the size
of the first leg (Spike).

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class FirstLegMeasuredMoveResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_SPIKE"
    spike_start_index: int = -1
    spike_end_index: int = -1
    spike_start_price: float = 0.0
    spike_end_price: float = 0.0
    spike_size: float = 0.0
    measured_move_target: float = 0.0
    progress_ratio: float = 0.0
    distance_to_target: float = 0.0
    target_reached: bool = False
    target_overshot: bool = False
    strong_spike: bool = False
    target_magnet_active: bool = False
    profit_taking_zone: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class FirstLegMeasuredMoveDynamics:
    """Project a 1=1 measured move from a strong first-leg spike."""

    MIN_HISTORY = 8
    MAX_SPIKE_BARS = 4
    MIN_BODY_RATIO = 0.60
    MIN_ALIGNED_RATIO = 0.75

    def analyze(self, candles):
        # Last candle is treated as current/forming and excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return FirstLegMeasuredMoveResult(reasons=("INSUFFICIENT_HISTORY",))

        spike = self._find_spike(closed)
        if spike is None:
            return FirstLegMeasuredMoveResult(reasons=("NO_STRONG_SPIKE",))

        start, end, direction, quality = spike
        first = closed[start]
        last = closed[end]

        # Brooks' preferred measurement for a very strong spike:
        # open of first spike bar to close of final spike bar.
        start_price = float(first.open)
        end_price = float(last.close)
        spike_size = abs(end_price - start_price)

        if spike_size <= 0:
            return FirstLegMeasuredMoveResult(reasons=("INVALID_SPIKE_SIZE",))

        if direction == "BUY":
            target = end_price + spike_size
            best_price = max(float(x.high) for x in closed[end:])
            progress = max(0.0, best_price - end_price) / spike_size
            distance = target - float(closed[-1].close)
            reached = best_price >= target
            overshot = best_price > target + spike_size * 0.10
        else:
            target = end_price - spike_size
            best_price = min(float(x.low) for x in closed[end:])
            progress = max(0.0, end_price - best_price) / spike_size
            distance = float(closed[-1].close) - target
            reached = best_price <= target
            overshot = best_price < target - spike_size * 0.10

        progress = min(progress, 2.0)
        near_target = 0.75 <= progress < 1.0
        reasons = ["STRONG_FIRST_LEG_SPIKE", "FIRST_LEG_1_TO_1_TARGET"]

        if near_target:
            reasons.append("MEASURED_MOVE_MAGNET_NEAR")
        if reached:
            reasons.append("MEASURED_MOVE_TARGET_REACHED")
        if overshot:
            reasons.append("MEASURED_MOVE_TARGET_OVERSHOT")

        if overshot:
            state = "TARGET_OVERSHOT"
        elif reached:
            state = "TARGET_REACHED"
        elif near_target:
            state = "APPROACHING_TARGET"
        else:
            state = "TARGET_ACTIVE"

        return FirstLegMeasuredMoveResult(
            valid=True,
            direction=direction,
            state=state,
            spike_start_index=start,
            spike_end_index=end,
            spike_start_price=start_price,
            spike_end_price=end_price,
            spike_size=spike_size,
            measured_move_target=target,
            progress_ratio=progress,
            distance_to_target=max(distance, 0.0),
            target_reached=reached,
            target_overshot=overshot,
            strong_spike=quality >= 0.75,
            target_magnet_active=not reached,
            profit_taking_zone=near_target or reached,
            reasons=tuple(reasons),
        )

    def _find_spike(self, candles):
        # Search early/middle history for a compact directional burst and leave
        # enough bars afterward to evaluate the measured-move projection.
        latest_end = len(candles) - 3
        best = None

        for start in range(1, latest_end):
            for length in range(2, self.MAX_SPIKE_BARS + 1):
                end = start + length - 1
                if end > latest_end:
                    continue

                group = candles[start:end + 1]
                buy = sum(float(x.close) > float(x.open) for x in group)
                sell = sum(float(x.close) < float(x.open) for x in group)
                direction = "BUY" if buy >= sell else "SELL"
                aligned = buy if direction == "BUY" else sell
                aligned_ratio = aligned / length

                body_ratios = []
                for bar in group:
                    rng = max(float(bar.high) - float(bar.low), 1e-9)
                    body_ratios.append(abs(float(bar.close) - float(bar.open)) / rng)
                avg_body = sum(body_ratios) / length

                first_open = float(group[0].open)
                last_close = float(group[-1].close)
                displacement = last_close - first_open
                directional = displacement > 0 if direction == "BUY" else displacement < 0

                if (
                    aligned_ratio >= self.MIN_ALIGNED_RATIO
                    and avg_body >= self.MIN_BODY_RATIO
                    and directional
                ):
                    quality = (aligned_ratio + avg_body) / 2.0
                    candidate = (quality, abs(displacement), start, end, direction)
                    if best is None or candidate[:2] > best[:2]:
                        best = candidate

        if best is None:
            return None

        quality, _, start, end, direction = best
        return start, end, direction, quality
