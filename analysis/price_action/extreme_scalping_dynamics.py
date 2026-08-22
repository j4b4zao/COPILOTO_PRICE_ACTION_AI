"""
analysis/price_action/extreme_scalping_dynamics.py

Brooks Reversals - Chapter 16: Extreme Scalping.
Diagnostic-only layer for identifying mathematically demanding scalping profiles.

This module does not alter Score, Risk, Decision or order execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ExtremeScalpingResult:
    valid: bool = False
    status: str = "UNKNOWN"
    risk_points: float = 0.0
    reward_points: float = 0.0
    cost_points: float = 0.0
    risk_reward: float = 0.0
    breakeven_win_rate: float = 0.0
    expected_win_rate: float = 0.0
    expected_value_points: float = 0.0
    high_precision_required: bool = False
    extreme_scalping_profile: bool = False
    suitable_for_copiloto: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ExtremeScalpingDynamics:
    """Evaluate whether a scalp profile demands unrealistic precision."""

    HIGH_PRECISION_THRESHOLD = 0.70

    def analyze(
        self,
        *,
        risk_points,
        reward_points,
        expected_win_rate=None,
        cost_points=0.0,
        trades_per_day=None,
    ):
        try:
            risk = float(risk_points)
            reward = float(reward_points)
            cost = max(float(cost_points or 0.0), 0.0)
        except (TypeError, ValueError):
            return ExtremeScalpingResult(
                reasons=("INVALID_NUMERIC_INPUT",),
            )

        if risk <= 0 or reward <= 0:
            return ExtremeScalpingResult(
                reasons=("INVALID_RISK_REWARD_GEOMETRY",),
            )

        net_reward = reward - cost
        net_loss = risk + cost

        if net_reward <= 0:
            return ExtremeScalpingResult(
                valid=True,
                status="EXTREME_SCALPING_UNSUITABLE",
                risk_points=risk,
                reward_points=reward,
                cost_points=cost,
                risk_reward=round(reward / risk, 3),
                breakeven_win_rate=1.0,
                high_precision_required=True,
                extreme_scalping_profile=True,
                suitable_for_copiloto=False,
                reasons=(
                    "TRADING_COST_CONSUMES_REWARD",
                    "NEGATIVE_EXPECTANCY_PROFILE",
                ),
            )

        rr = reward / risk
        breakeven = net_loss / (net_reward + net_loss)

        if expected_win_rate is None:
            expected = 0.0
            expectancy = 0.0
            expected_provided = False
        else:
            try:
                expected = float(expected_win_rate)
            except (TypeError, ValueError):
                return ExtremeScalpingResult(
                    reasons=("INVALID_EXPECTED_WIN_RATE",),
                )

            if expected > 1.0:
                expected /= 100.0

            if not 0.0 <= expected <= 1.0:
                return ExtremeScalpingResult(
                    reasons=("INVALID_EXPECTED_WIN_RATE",),
                )

            expected_provided = True
            expectancy = expected * net_reward - (1.0 - expected) * net_loss

        high_precision = breakeven >= self.HIGH_PRECISION_THRESHOLD
        extreme_profile = rr < 1.0 or high_precision

        if high_precision:
            status = "EXTREME_SCALPING_UNSUITABLE"
            suitable = False
        elif expected_provided and expected <= breakeven:
            status = "SCALPING_EXPECTANCY_UNFAVORABLE"
            suitable = False
        elif rr < 1.0:
            status = "HIGH_PRECISION_SCALPING"
            suitable = False
        elif rr < 2.0:
            status = "SCALPING_MATH_ACCEPTABLE"
            suitable = True
        else:
            status = "FAVORABLE_REWARD_RISK_PROFILE"
            suitable = True

        reasons = [
            f"RISK_REWARD_{rr:.2f}",
            f"BREAKEVEN_WIN_RATE_{breakeven:.1%}",
        ]

        if cost > 0:
            reasons.append("COSTS_INCLUDED_IN_EXPECTANCY")
        if high_precision:
            reasons.append("REQUIRES_AT_LEAST_70_PERCENT_BREAK_EVEN_ACCURACY")
        if rr < 1.0:
            reasons.append("RISK_GREATER_THAN_REWARD")
        elif rr >= 2.0:
            reasons.append("REWARD_AT_LEAST_TWO_TIMES_RISK")
        else:
            reasons.append("REWARD_AT_LEAST_EQUAL_TO_RISK")

        if expected_provided:
            reasons.append(f"EXPECTED_WIN_RATE_{expected:.1%}")
            if expectancy > 0:
                reasons.append("POSITIVE_EXPECTANCY_AT_PROVIDED_WIN_RATE")
            elif expectancy < 0:
                reasons.append("NEGATIVE_EXPECTANCY_AT_PROVIDED_WIN_RATE")
            else:
                reasons.append("BREAKEVEN_EXPECTANCY_AT_PROVIDED_WIN_RATE")

        if trades_per_day is not None:
            try:
                frequency = int(trades_per_day)
                if frequency >= 20:
                    reasons.append("VERY_HIGH_TRADE_FREQUENCY")
            except (TypeError, ValueError):
                reasons.append("INVALID_TRADE_FREQUENCY_IGNORED")

        return ExtremeScalpingResult(
            valid=True,
            status=status,
            risk_points=round(risk, 4),
            reward_points=round(reward, 4),
            cost_points=round(cost, 4),
            risk_reward=round(rr, 3),
            breakeven_win_rate=round(breakeven, 4),
            expected_win_rate=round(expected, 4),
            expected_value_points=round(expectancy, 4),
            high_precision_required=high_precision,
            extreme_scalping_profile=extreme_profile,
            suitable_for_copiloto=suitable,
            reasons=tuple(reasons),
        )
