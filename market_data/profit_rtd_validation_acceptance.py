"""Avalia a qualidade de uma sessão de validação Profit RTD (RC13)."""

from __future__ import annotations

from dataclasses import dataclass

from market_data.profit_rtd_validation_recorder import ProfitRTDValidationSnapshot


@dataclass(frozen=True, slots=True)
class ProfitRTDValidationAcceptancePolicy:
    min_cycles: int = 300
    min_new_trades: int = 100
    min_continuity_rate: float = 0.98
    max_continuity_loss_rate: float = 0.02
    min_update_rate: float = 0.01

    def __post_init__(self):
        if self.min_cycles <= 0:
            raise ValueError("min_cycles deve ser positivo.")
        if self.min_new_trades < 0:
            raise ValueError("min_new_trades não pode ser negativo.")
        for name in ("min_continuity_rate", "max_continuity_loss_rate", "min_update_rate"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} deve estar entre 0 e 1.")


@dataclass(frozen=True, slots=True)
class ProfitRTDValidationAcceptanceResult:
    verdict: str
    reasons: tuple[str, ...]
    total_cycles: int
    total_new_trades: int
    update_rate: float
    continuity_rate: float
    continuity_loss_rate: float
    observational_only: bool = True
    score_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class ProfitRTDValidationAcceptanceEvaluator:
    """Classifica uma sessão como PASS, REVIEW ou FAIL sem habilitar operação."""

    NAME = "ProfitRTDValidationAcceptanceEvaluator"
    VERSION = "RC13"

    def __init__(self, policy: ProfitRTDValidationAcceptancePolicy | None = None):
        self.policy = policy or ProfitRTDValidationAcceptancePolicy()

    def evaluate(
        self,
        snapshot: ProfitRTDValidationSnapshot,
    ) -> ProfitRTDValidationAcceptanceResult:
        if not isinstance(snapshot, ProfitRTDValidationSnapshot):
            raise TypeError("snapshot deve ser ProfitRTDValidationSnapshot.")

        security_reasons = self._security_failures(snapshot)
        total = int(snapshot.total_cycles)
        continuity_loss_rate = (
            float(snapshot.continuity_loss_cycles) / total if total else 0.0
        )

        fail_reasons = list(security_reasons)
        if total > 0 and continuity_loss_rate > self.policy.max_continuity_loss_rate:
            fail_reasons.append("CONTINUITY_LOSS_RATE_HIGH")

        if fail_reasons:
            verdict = "FAIL"
            reasons = tuple(fail_reasons)
        else:
            review_reasons = []
            if total < self.policy.min_cycles:
                review_reasons.append("INSUFFICIENT_CYCLES")
            if snapshot.total_new_trades < self.policy.min_new_trades:
                review_reasons.append("INSUFFICIENT_NEW_TRADES")
            if snapshot.continuity_rate < self.policy.min_continuity_rate:
                review_reasons.append("CONTINUITY_RATE_LOW")
            if snapshot.update_rate < self.policy.min_update_rate:
                review_reasons.append("UPDATE_RATE_LOW")

            if review_reasons:
                verdict = "REVIEW"
                reasons = tuple(review_reasons)
            else:
                verdict = "PASS"
                reasons = ("ACCEPTANCE_CRITERIA_MET",)

        return ProfitRTDValidationAcceptanceResult(
            verdict=verdict,
            reasons=reasons,
            total_cycles=total,
            total_new_trades=int(snapshot.total_new_trades),
            update_rate=float(snapshot.update_rate),
            continuity_rate=float(snapshot.continuity_rate),
            continuity_loss_rate=round(continuity_loss_rate, 4),
        )

    @staticmethod
    def _security_failures(snapshot: ProfitRTDValidationSnapshot) -> list[str]:
        reasons = []
        if not snapshot.observational_only:
            reasons.append("NOT_OBSERVATIONAL")
        if snapshot.score_influence_allowed:
            reasons.append("SCORE_INFLUENCE_ENABLED")
        if snapshot.decision_influence_allowed:
            reasons.append("DECISION_INFLUENCE_ENABLED")
        if snapshot.order_execution_allowed:
            reasons.append("ORDER_EXECUTION_ENABLED")
        return reasons
