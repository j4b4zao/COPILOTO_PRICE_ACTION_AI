"""
analysis/price_action/gap_range_measured_move_dynamics.py

Brooks Trading Ranges - Chapter 8:
Measured Moves based on Gaps and Trading Ranges.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class GapRangeMeasuredMoveResult:
    valid: bool = False
    direction: str = "NONE"
    source: str = "NONE"
    state: str = "NO_TARGET"

    gap_index: int = -1
    gap_low: float = 0.0
    gap_high: float = 0.0
    gap_midpoint: float = 0.0
    gap_origin: float = 0.0
    gap_target: float = 0.0

    range_start_index: int = -1
    range_end_index: int = -1
    range_low: float = 0.0
    range_high: float = 0.0
    range_height: float = 0.0
    range_breakout_level: float = 0.0
    range_target: float = 0.0

    primary_target: float = 0.0
    current_price: float = 0.0
    distance_to_target: float = 0.0
    progress_ratio: float = 0.0

    gap_target_active: bool = False
    range_target_active: bool = False
    target_confluence: bool = False
    approaching_target: bool = False
    target_reached: bool = False
    target_overshot: bool = False
    profit_taking_zone: bool = False
    reversal_watch: bool = False

    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class GapRangeMeasuredMoveDynamics:
    """Project measured-move magnets from gaps and trading ranges."""

    MIN_HISTORY = 9
    RANGE_WINDOW = 6
    APPROACH_RATIO = 0.85
    CONFLUENCE_TOLERANCE = 0.12

    def analyze(self, candles):
        # The last element is treated as the current/forming candle.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return GapRangeMeasuredMoveResult(reasons=("INSUFFICIENT_HISTORY",))

        current_price = float(closed[-1].close)
        gap = self._find_latest_gap(closed)
        range_projection = self._find_latest_range_breakout(closed)

        if gap is None and range_projection is None:
            return GapRangeMeasuredMoveResult(
                current_price=current_price,
                reasons=("NO_MEASURED_MOVE_SOURCE",),
            )

        reasons = []
        direction = "NONE"

        gap_index = -1
        gap_low = gap_high = gap_midpoint = gap_origin = gap_target = 0.0
        gap_active = False

        if gap is not None:
            gap_index, gap_direction, gap_low, gap_high = gap
            gap_midpoint = (gap_low + gap_high) / 2.0
            gap_origin = self._trend_origin_before_gap(closed, gap_index, gap_direction)
            if gap_direction == "BUY":
                gap_target = gap_midpoint + (gap_midpoint - gap_origin)
            else:
                gap_target = gap_midpoint - (gap_origin - gap_midpoint)
            gap_active = self._target_is_ahead(current_price, gap_target, gap_direction)
            direction = gap_direction
            reasons.append("GAP_MEASURED_MOVE")

        rs = re = -1
        range_low = range_high = range_height = breakout_level = range_target = 0.0
        range_active = False

        if range_projection is not None:
            (
                rs,
                re,
                range_direction,
                range_low,
                range_high,
                breakout_level,
            ) = range_projection
            range_height = range_high - range_low
            if range_direction == "BUY":
                range_target = breakout_level + range_height
            else:
                range_target = breakout_level - range_height
            range_active = self._target_is_ahead(current_price, range_target, range_direction)
            if direction == "NONE":
                direction = range_direction
            reasons.append("TRADING_RANGE_MEASURED_MOVE")

        # Prefer the nearest still-relevant target in the same direction.
        candidates = []
        if gap_target:
            candidates.append(("GAP", gap_target))
        if range_target:
            candidates.append(("RANGE", range_target))

        same_direction_targets = [
            item for item in candidates
            if direction == "BUY" and item[1] >= min(current_price, item[1])
            or direction == "SELL" and item[1] <= max(current_price, item[1])
        ]
        if not same_direction_targets:
            same_direction_targets = candidates

        source, primary_target = min(
            same_direction_targets,
            key=lambda item: abs(item[1] - current_price),
        )

        # Confluence if both projections exist and are close relative to range size
        # (or relative to current price when no range projection exists).
        confluence = False
        if gap_target and range_target:
            scale = max(range_height, abs(current_price) * 0.001, 1e-9)
            confluence = abs(gap_target - range_target) <= scale * self.CONFLUENCE_TOLERANCE
            if confluence:
                reasons.append("TARGET_CONFLUENCE")

        origin = gap_origin if source == "GAP" and gap_origin else breakout_level
        denom = abs(primary_target - origin)
        progress = 0.0 if denom <= 1e-9 else abs(current_price - origin) / denom
        distance = abs(primary_target - current_price)

        if direction == "BUY":
            reached = current_price >= primary_target
            overshot = current_price > primary_target and progress >= 1.08
        else:
            reached = current_price <= primary_target
            overshot = current_price < primary_target and progress >= 1.08

        approaching = not reached and progress >= self.APPROACH_RATIO
        profit_zone = approaching or reached
        reversal_watch = reached or overshot

        if overshot:
            state = "TARGET_OVERSHOT"
        elif reached:
            state = "TARGET_REACHED"
        elif approaching:
            state = "APPROACHING_TARGET"
        else:
            state = "TARGET_ACTIVE"

        if approaching:
            reasons.append("APPROACHING_MAGNET")
        if reached:
            reasons.append("MEASURED_MOVE_REACHED")
        if overshot:
            reasons.append("MEASURED_MOVE_OVERSHOOT")

        return GapRangeMeasuredMoveResult(
            valid=True,
            direction=direction,
            source=source,
            state=state,
            gap_index=gap_index,
            gap_low=gap_low,
            gap_high=gap_high,
            gap_midpoint=gap_midpoint,
            gap_origin=gap_origin,
            gap_target=gap_target,
            range_start_index=rs,
            range_end_index=re,
            range_low=range_low,
            range_high=range_high,
            range_height=range_height,
            range_breakout_level=breakout_level,
            range_target=range_target,
            primary_target=primary_target,
            current_price=current_price,
            distance_to_target=distance,
            progress_ratio=progress,
            gap_target_active=gap_active,
            range_target_active=range_active,
            target_confluence=confluence,
            approaching_target=approaching,
            target_reached=reached,
            target_overshot=overshot,
            profit_taking_zone=profit_zone,
            reversal_watch=reversal_watch,
            reasons=tuple(reasons),
        )

    def _find_latest_gap(self, candles):
        for idx in range(len(candles) - 1, 0, -1):
            prev = candles[idx - 1]
            bar = candles[idx]
            if float(bar.low) > float(prev.high):
                return idx, "BUY", float(prev.high), float(bar.low)
            if float(bar.high) < float(prev.low):
                return idx, "SELL", float(bar.high), float(prev.low)
        return None

    def _trend_origin_before_gap(self, candles, gap_index, direction):
        start = max(0, gap_index - 8)
        prior = candles[start:gap_index]
        if not prior:
            return float(candles[gap_index].open)
        if direction == "BUY":
            return min(float(x.low) for x in prior)
        return max(float(x.high) for x in prior)

    def _find_latest_range_breakout(self, candles):
        # Scan backward for a breakout following a compact 6-bar range.
        for idx in range(len(candles) - 1, self.RANGE_WINDOW - 1, -1):
            window = candles[idx - self.RANGE_WINDOW:idx]
            range_high = max(float(x.high) for x in window)
            range_low = min(float(x.low) for x in window)
            height = range_high - range_low
            if height <= 0:
                continue

            avg_bar_range = sum(
                max(float(x.high) - float(x.low), 0.0) for x in window
            ) / len(window)

            # Avoid treating a directional run as a trading range.
            if height > max(avg_bar_range * 4.0, 1e-9):
                continue

            bar = candles[idx]
            if float(bar.close) > range_high:
                return (
                    idx - self.RANGE_WINDOW,
                    idx - 1,
                    "BUY",
                    range_low,
                    range_high,
                    range_high,
                )
            if float(bar.close) < range_low:
                return (
                    idx - self.RANGE_WINDOW,
                    idx - 1,
                    "SELL",
                    range_low,
                    range_high,
                    range_low,
                )
        return None

    @staticmethod
    def _target_is_ahead(current_price, target, direction):
        if not target:
            return False
        if direction == "BUY":
            return current_price < target
        return current_price > target
