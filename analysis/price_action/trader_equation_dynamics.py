"""
analysis/price_action/trader_equation_dynamics.py

Brooks Trading Ranges - Chapter 25:
Trading Mathematics / Trader's Equation.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TraderEquationResult:
    valid: bool = False
    direction: str = "NONE"
    probability_success: float = 0.0
    probability_failure: float = 0.0
    probability_source: str = "NONE"
    entry_price: float = 0.0
    stop_price: float = 0.0
    target_price: float = 0.0
    risk_points: float = 0.0
    reward_points: float = 0.0
    reward_risk: float = 0.0
    breakeven_probability: float = 0.0
    expected_value_points: float = 0.0
    expectancy_r: float = 0.0
    edge_points: float = 0.0
    equation_state: str = "INVALID"
    favorable: bool = False
    marginal: bool = False
    current_candle_used: bool = False
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TraderEquationDynamics:
    """Evaluate probability x reward versus failure probability x risk."""

    DEFAULT_UNCERTAIN_PROBABILITY = 0.50
    DEFAULT_GOOD_SETUP_PROBABILITY = 0.60
    DEFAULT_LOW_PROBABILITY = 0.40
    MARGINAL_EDGE_R = 0.10
    STRONG_EDGE_R = 0.50

    def analyze(
        self,
        entry_price,
        stop_price,
        target_price,
        probability_success=None,
        setup_quality="UNCERTAIN",
        direction=None,
    ):
        entry = self._to_float(entry_price)
        stop = self._to_float(stop_price)
        target = self._to_float(target_price)

        resolved_direction = self._resolve_direction(
            entry,
            stop,
            target,
            direction,
        )

        if resolved_direction == "NONE":
            return TraderEquationResult(
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                reason="INVALID_TRADE_GEOMETRY",
                reasons=("INVALID_TRADE_GEOMETRY",),
            )

        risk = abs(entry - stop)
        reward = abs(target - entry)

        if risk <= 0 or reward <= 0:
            return TraderEquationResult(
                direction=resolved_direction,
                entry_price=entry,
                stop_price=stop,
                target_price=target,
                reason="INVALID_RISK_OR_REWARD",
                reasons=("INVALID_RISK_OR_REWARD",),
            )

        probability, source = self._resolve_probability(
            probability_success,
            setup_quality,
        )

        failure_probability = 1.0 - probability
        reward_risk = reward / risk
        breakeven_probability = risk / (risk + reward)

        positive_side = probability * reward
        negative_side = failure_probability * risk
        edge_points = positive_side - negative_side
        expectancy_r = edge_points / risk

        if expectancy_r >= self.STRONG_EDGE_R:
            state = "STRONGLY_FAVORABLE"
            favorable = True
            marginal = False
        elif expectancy_r > self.MARGINAL_EDGE_R:
            state = "FAVORABLE"
            favorable = True
            marginal = False
        elif expectancy_r > 0:
            state = "MARGINAL_POSITIVE"
            favorable = True
            marginal = True
        elif abs(expectancy_r) <= 1e-9:
            state = "BREAKEVEN"
            favorable = False
            marginal = True
        else:
            state = "UNFAVORABLE"
            favorable = False
            marginal = False

        reasons = [
            f"PROBABILITY_SOURCE_{source}",
            f"SUCCESS_PROBABILITY_{probability:.2f}",
            f"REWARD_RISK_{reward_risk:.2f}",
            f"BREAKEVEN_PROBABILITY_{breakeven_probability:.3f}",
            f"EXPECTANCY_R_{expectancy_r:.3f}",
        ]

        if probability < breakeven_probability:
            reasons.append("PROBABILITY_BELOW_BREAKEVEN")
        elif probability > breakeven_probability:
            reasons.append("PROBABILITY_ABOVE_BREAKEVEN")
        else:
            reasons.append("PROBABILITY_AT_BREAKEVEN")

        if reward_risk < 1.0:
            reasons.append("REWARD_SMALLER_THAN_RISK_REQUIRES_HIGH_WIN_RATE")

        if probability <= 0.40 and reward_risk > 1.0 and favorable:
            reasons.append("LOW_PROBABILITY_COMPENSATED_BY_LARGE_REWARD")

        return TraderEquationResult(
            valid=True,
            direction=resolved_direction,
            probability_success=round(probability, 4),
            probability_failure=round(failure_probability, 4),
            probability_source=source,
            entry_price=entry,
            stop_price=stop,
            target_price=target,
            risk_points=round(risk, 6),
            reward_points=round(reward, 6),
            reward_risk=round(reward_risk, 6),
            breakeven_probability=round(breakeven_probability, 6),
            expected_value_points=round(edge_points, 6),
            expectancy_r=round(expectancy_r, 6),
            edge_points=round(edge_points, 6),
            equation_state=state,
            favorable=favorable,
            marginal=marginal,
            current_candle_used=False,
            reason=state,
            reasons=tuple(reasons),
        )

    def _resolve_probability(self, explicit_probability, setup_quality):
        if explicit_probability is not None:
            probability = self._to_float(explicit_probability)
            if probability > 1.0 and probability <= 100.0:
                probability /= 100.0
            probability = min(max(probability, 0.0), 1.0)
            return probability, "EXPLICIT"

        quality = str(setup_quality or "UNCERTAIN").upper().strip()

        if quality in {
            "GOOD",
            "STRONG",
            "HIGH",
            "A",
            "A+",
            "CONFIDENT",
        }:
            return self.DEFAULT_GOOD_SETUP_PROBABILITY, "GOOD_SETUP_DEFAULT"

        if quality in {
            "LOW_PROBABILITY",
            "UNLIKELY",
            "SPECULATIVE",
        }:
            return self.DEFAULT_LOW_PROBABILITY, "LOW_PROBABILITY_DEFAULT"

        return self.DEFAULT_UNCERTAIN_PROBABILITY, "UNCERTAIN_DEFAULT"

    @staticmethod
    def _resolve_direction(entry, stop, target, direction):
        supplied = str(direction or "").upper().strip()
        if supplied in {"BUY", "LONG"}:
            return "BUY" if stop < entry < target else "NONE"
        if supplied in {"SELL", "SHORT"}:
            return "SELL" if target < entry < stop else "NONE"

        if stop < entry < target:
            return "BUY"
        if target < entry < stop:
            return "SELL"
        return "NONE"

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
