"""
analysis/price_action/trading_guidelines_dynamics.py

Brooks Reversals - Chapter 25:
Trading Guidelines.

Diagnostic-only layer. It does not alter Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TradingGuidelinesResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    context_clear: bool = False
    setup_confirmed: bool = False
    reward_risk_ok: bool = False
    conflict_present: bool = False
    overtrading_risk: bool = False
    chase_risk: bool = False
    discipline_score: float = 0.0
    guideline_veto: bool = False
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TradingGuidelinesDynamics:
    """Apply final trading-discipline guidelines without generating a trade."""

    def analyze(
        self,
        *,
        direction="NONE",
        context_clear=False,
        setup_confirmed=False,
        reward_risk=0.0,
        conflict_present=False,
        trades_today=0,
        max_preferred_trades=5,
        chase_risk=False,
    ):
        direction = str(direction or "NONE").upper()
        if direction not in {"BUY", "SELL", "NONE"}:
            direction = "NONE"

        rr = max(float(reward_risk or 0.0), 0.0)
        trades_today = max(int(trades_today or 0), 0)
        max_preferred_trades = max(int(max_preferred_trades or 1), 1)

        rr_ok = rr >= 1.0
        overtrading = trades_today > max_preferred_trades

        score = 100.0
        reasons = []

        if direction == "NONE":
            score -= 20.0
            reasons.append("NO_DIRECTIONAL_THESIS")
        if not context_clear:
            score -= 20.0
            reasons.append("UNCLEAR_CONTEXT")
        if not setup_confirmed:
            score -= 20.0
            reasons.append("SETUP_NOT_CONFIRMED")
        if not rr_ok:
            score -= 20.0
            reasons.append("REWARD_RISK_BELOW_1R")
        if conflict_present:
            score -= 25.0
            reasons.append("CONFLICT_PRESENT")
        if overtrading:
            score -= 15.0
            reasons.append("OVERTRADING_RISK")
        if chase_risk:
            score -= 15.0
            reasons.append("CHASE_RISK")

        score = max(min(score, 100.0), 0.0)

        hard_veto = conflict_present or chase_risk or rr < 0.75
        soft_veto = (not context_clear and not setup_confirmed) or overtrading
        veto = hard_veto or soft_veto

        if hard_veto:
            status = "GUIDELINE_VETO"
        elif soft_veto:
            status = "GUIDELINE_CAUTION"
        elif score >= 85.0:
            status = "GUIDELINES_STRONG_DISCIPLINE"
        elif score >= 65.0:
            status = "GUIDELINES_ACCEPTABLE"
        else:
            status = "GUIDELINES_WEAK_DISCIPLINE"

        if not reasons:
            reasons.append("GUIDELINES_RESPECTED")

        return TradingGuidelinesResult(
            valid=True,
            status=status,
            direction=direction,
            context_clear=bool(context_clear),
            setup_confirmed=bool(setup_confirmed),
            reward_risk_ok=rr_ok,
            conflict_present=bool(conflict_present),
            overtrading_risk=overtrading,
            chase_risk=bool(chase_risk),
            discipline_score=score,
            guideline_veto=veto,
            reasons=tuple(reasons),
        )
