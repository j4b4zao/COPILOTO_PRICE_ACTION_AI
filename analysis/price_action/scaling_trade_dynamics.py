"""
analysis/price_action/scaling_trade_dynamics.py

Brooks Trading Ranges - Chapter 31:
Scaling Into and Out of a Trade.

Diagnostic-only layer. It does not send orders and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ScalingTradeResult:
    valid: bool = False
    direction: str = "NONE"
    action: str = "NONE"
    state: str = "NO_ACTION"
    average_entry: float = 0.0
    total_size: float = 0.0
    initial_risk: float = 0.0
    aggregate_risk: float = 0.0
    aggregate_risk_r: float = 0.0
    favorable_scale_in: bool = False
    averaging_down_risk: bool = False
    scale_out_appropriate: bool = False
    risk_limit_exceeded: bool = False
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ScalingTradeDynamics:
    """Evaluate whether scaling in/out is coherent with structure and risk."""

    MAX_AGGREGATE_R = 1.0

    def analyze(
        self,
        direction,
        entries,
        stop_price,
        current_price,
        action,
        action_price=None,
        action_size=0.0,
        structure_confirmed=False,
        target_near=False,
        deterioration=False,
    ):
        direction = str(direction).upper()
        action = str(action).upper()

        if direction not in ("BUY", "SELL"):
            return ScalingTradeResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        normalized = []
        for item in entries or []:
            if isinstance(item, dict):
                price = float(item.get("price", 0.0) or 0.0)
                size = float(item.get("size", 0.0) or 0.0)
            else:
                price = float(item[0])
                size = float(item[1])
            if price > 0 and size > 0:
                normalized.append((price, size))

        if not normalized:
            return ScalingTradeResult(
                direction=direction,
                action=action,
                reason="NO_POSITION",
                reasons=("NO_POSITION",),
            )

        stop = float(stop_price)
        current = float(current_price)
        total_size = sum(size for _, size in normalized)
        average_entry = sum(price * size for price, size in normalized) / total_size
        initial_risk = abs(normalized[0][0] - stop)

        if initial_risk <= 0:
            return ScalingTradeResult(
                direction=direction,
                action=action,
                reason="INVALID_INITIAL_RISK",
                reasons=("INVALID_INITIAL_RISK",),
            )

        aggregate_risk = self._aggregate_risk(normalized, stop)
        reasons = []

        favorable_scale_in = False
        averaging_down_risk = False
        scale_out_appropriate = False
        risk_limit_exceeded = False
        state = "HOLD_POSITION"

        if action == "SCALE_IN":
            price = float(action_price or 0.0)
            size = float(action_size or 0.0)
            if price <= 0 or size <= 0:
                return ScalingTradeResult(
                    valid=False,
                    direction=direction,
                    action=action,
                    average_entry=average_entry,
                    total_size=total_size,
                    initial_risk=initial_risk,
                    aggregate_risk=aggregate_risk,
                    aggregate_risk_r=aggregate_risk / (initial_risk * total_size),
                    reason="INVALID_SCALE_IN",
                    reasons=("INVALID_SCALE_IN",),
                )

            losing_add = (
                direction == "BUY" and price < average_entry
            ) or (
                direction == "SELL" and price > average_entry
            )

            if losing_add and not structure_confirmed:
                averaging_down_risk = True
                state = "SCALE_IN_BLOCKED_AVERAGING_DOWN"
                reasons.append("ADDING_TO_LOSER_WITHOUT_STRUCTURE")
            else:
                candidate = normalized + [(price, size)]
                candidate_risk = self._aggregate_risk(candidate, stop)
                candidate_total = total_size + size
                candidate_r = candidate_risk / (initial_risk * candidate_total)

                if candidate_r > self.MAX_AGGREGATE_R:
                    risk_limit_exceeded = True
                    state = "SCALE_IN_BLOCKED_RISK"
                    reasons.append("AGGREGATE_RISK_LIMIT_EXCEEDED")
                else:
                    favorable_scale_in = True
                    state = "SCALE_IN_ALLOWED"
                    aggregate_risk = candidate_risk
                    total_size = candidate_total
                    average_entry = (
                        sum(p * s for p, s in candidate) / candidate_total
                    )
                    reasons.append("STRUCTURE_AND_RISK_SUPPORT_SCALE_IN")

        elif action == "SCALE_OUT":
            if target_near or deterioration:
                scale_out_appropriate = True
                state = "SCALE_OUT_APPROPRIATE"
                if target_near:
                    reasons.append("STRUCTURAL_TARGET_NEAR")
                if deterioration:
                    reasons.append("CONTEXT_DETERIORATION")
            else:
                state = "SCALE_OUT_EARLY"
                reasons.append("NO_TARGET_OR_DETERIORATION_YET")

        elif action == "HOLD":
            state = "HOLD_POSITION"
            reasons.append("NO_SCALING_ACTION_REQUESTED")
        else:
            return ScalingTradeResult(
                direction=direction,
                action=action,
                reason="INVALID_ACTION",
                reasons=("INVALID_ACTION",),
            )

        aggregate_r = aggregate_risk / (initial_risk * max(total_size, 1e-9))

        return ScalingTradeResult(
            valid=True,
            direction=direction,
            action=action,
            state=state,
            average_entry=round(average_entry, 4),
            total_size=round(total_size, 4),
            initial_risk=round(initial_risk, 4),
            aggregate_risk=round(aggregate_risk, 4),
            aggregate_risk_r=round(aggregate_r, 4),
            favorable_scale_in=favorable_scale_in,
            averaging_down_risk=averaging_down_risk,
            scale_out_appropriate=scale_out_appropriate,
            risk_limit_exceeded=risk_limit_exceeded,
            reason=reasons[-1] if reasons else "",
            reasons=tuple(reasons),
        )

    @staticmethod
    def _aggregate_risk(entries, stop):
        return sum(abs(price - stop) * size for price, size in entries)
