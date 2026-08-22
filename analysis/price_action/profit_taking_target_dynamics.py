"""
analysis/price_action/profit_taking_target_dynamics.py

Brooks Trading Ranges - Chapter 30:
Profit Taking and Profit Targets.

Diagnostic-only layer. It does not authorize trades, send orders, or mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ProfitTakingTargetResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_TARGET"
    entry_price: float = 0.0
    target_price: float = 0.0
    target_source: str = "NONE"
    risk_points: float = 0.0
    reward_points: float = 0.0
    reward_risk: float = 0.0
    progress: float = 0.0
    distance_to_target: float = 0.0
    target_zone: bool = False
    partial_profit_zone: bool = False
    target_reached: bool = False
    target_overshot: bool = False
    heavy_profit_taking: bool = False
    correction_risk: bool = False
    reversal_risk: bool = False
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ProfitTakingTargetDynamics:
    """Track structural profit targets and evidence of profit-taking pressure."""

    MIN_HISTORY = 8
    SAMPLE = 12
    TARGET_ZONE_FRACTION = 0.15
    PARTIAL_ZONE_PROGRESS = 0.75

    def analyze(
        self,
        candles,
        direction,
        entry_price,
        structural_target=None,
        stop_price=None,
        target_source="STRUCTURAL",
    ):
        direction = str(direction or "").upper()
        if direction not in ("BUY", "SELL"):
            return ProfitTakingTargetResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        # Last candle is assumed current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ProfitTakingTargetResult(
                direction=direction,
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        entry = float(entry_price or 0.0)
        if entry <= 0:
            return ProfitTakingTargetResult(
                direction=direction,
                reason="INVALID_ENTRY",
                reasons=("INVALID_ENTRY",),
            )

        target = self._resolve_target(
            closed,
            direction,
            entry,
            structural_target,
        )
        source = target_source if structural_target is not None else "RECENT_EXTREME"

        if target <= 0 or not self._valid_geometry(direction, entry, target):
            return ProfitTakingTargetResult(
                direction=direction,
                entry_price=entry,
                reason="NO_VALID_TARGET",
                reasons=("NO_VALID_TARGET",),
            )

        stop = float(stop_price or 0.0)
        risk = abs(entry - stop) if stop > 0 else 0.0
        reward = abs(target - entry)
        rr = reward / risk if risk > 0 else 0.0

        last_close = float(closed[-1].close)
        if direction == "BUY":
            favorable_move = last_close - entry
            distance = target - last_close
            reached = last_close >= target
        else:
            favorable_move = entry - last_close
            distance = last_close - target
            reached = last_close <= target

        progress = favorable_move / reward if reward > 0 else 0.0
        progress = max(0.0, progress)
        overshot = progress > 1.05
        target_zone = distance <= max(reward * self.TARGET_ZONE_FRACTION, 1e-9)
        target_zone = target_zone and not overshot
        partial_zone = progress >= self.PARTIAL_ZONE_PROGRESS and not overshot

        sample = closed[-self.SAMPLE:]
        heavy_profit_taking = self._heavy_profit_taking(sample, direction)
        correction_risk = heavy_profit_taking and progress >= 0.65
        reversal_risk = self._reversal_pressure(sample, direction) and reached

        reasons = [f"TARGET_{source}"]
        if rr > 0:
            reasons.append(f"RR_{rr:.2f}")

        if overshot:
            state = "TARGET_OVERSHOT"
            reasons.append("TARGET_OVERSHOT")
        elif reached:
            state = "TARGET_REACHED"
            reasons.append("TARGET_REACHED")
        elif target_zone:
            state = "PROFIT_TAKING_ZONE"
            reasons.append("APPROACHING_STRUCTURAL_MAGNET")
        elif partial_zone:
            state = "PARTIAL_PROFIT_ZONE"
            reasons.append("PARTIAL_PROFIT_REASONABLE")
        else:
            state = "TARGET_ACTIVE"
            reasons.append("TARGET_STILL_ACTIVE")

        if heavy_profit_taking:
            reasons.append("HEAVY_PROFIT_TAKING")
        if correction_risk:
            reasons.append("CORRECTION_RISK")
        if reversal_risk:
            reasons.append("REVERSAL_RISK")

        return ProfitTakingTargetResult(
            valid=True,
            direction=direction,
            state=state,
            entry_price=entry,
            target_price=round(target, 6),
            target_source=source,
            risk_points=round(risk, 6),
            reward_points=round(reward, 6),
            reward_risk=round(rr, 3),
            progress=round(progress, 3),
            distance_to_target=round(distance, 6),
            target_zone=target_zone,
            partial_profit_zone=partial_zone,
            target_reached=reached,
            target_overshot=overshot,
            heavy_profit_taking=heavy_profit_taking,
            correction_risk=correction_risk,
            reversal_risk=reversal_risk,
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    @staticmethod
    def _resolve_target(candles, direction, entry, structural_target):
        if structural_target is not None:
            return float(structural_target)

        if direction == "BUY":
            candidates = [float(c.high) for c in candles if float(c.high) > entry]
            return min(candidates) if candidates else 0.0

        candidates = [float(c.low) for c in candles if float(c.low) < entry]
        return max(candidates) if candidates else 0.0

    @staticmethod
    def _valid_geometry(direction, entry, target):
        if direction == "BUY":
            return target > entry
        return target < entry

    @staticmethod
    def _heavy_profit_taking(candles, direction):
        if len(candles) < 4:
            return False

        recent = candles[-4:]
        against = 0
        long_wicks = 0

        for candle in recent:
            o = float(candle.open)
            h = float(candle.high)
            l = float(candle.low)
            c = float(candle.close)
            rng = max(h - l, 1e-9)

            if direction == "BUY":
                against += c < o
                long_wicks += (h - max(o, c)) / rng >= 0.35
            else:
                against += c > o
                long_wicks += (min(o, c) - l) / rng >= 0.35

        return against >= 2 or long_wicks >= 2

    @staticmethod
    def _reversal_pressure(candles, direction):
        if len(candles) < 3:
            return False

        recent = candles[-3:]
        if direction == "BUY":
            bearish = sum(float(c.close) < float(c.open) for c in recent)
            lower_closes = float(recent[-1].close) < float(recent[-2].close) < float(recent[-3].close)
            return bearish >= 2 and lower_closes

        bullish = sum(float(c.close) > float(c.open) for c in recent)
        higher_closes = float(recent[-1].close) > float(recent[-2].close) > float(recent[-3].close)
        return bullish >= 2 and higher_closes
