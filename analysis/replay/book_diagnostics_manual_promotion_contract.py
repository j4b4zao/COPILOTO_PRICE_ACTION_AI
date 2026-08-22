"""
BookDiagnostics RC21 - Manual Promotion Contract.

Cria um contrato passivo e auditavel para candidatos aprovados pelo RC20.
Nenhuma ativacao em runtime ocorre automaticamente.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

ALLOWED_TARGETS = {"EVIDENCE", "CONTEXT", "CHECKLIST", "RISK"}
MAX_INITIAL_WEIGHTS = {
    "EVIDENCE": 0.20,
    "CONTEXT": 0.15,
    "CHECKLIST": 1.00,
    "RISK": 0.10,
}


@dataclass(slots=True, frozen=True)
class ManualPromotionContract:
    version: str
    book_state: str
    target_layer: str
    initial_weight: float
    probation_samples: int
    rollback_edge_r: float
    rollback_stop_first_rate: float
    rollback_direction_correct_rate: float
    source_recommendation: str
    manual_approval_required: bool
    runtime_active: bool
    status: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsManualPromotionContractBuilder:
    VERSION = "RC21-MANUAL-PROMOTION-CONTRACT"

    def __init__(self, *, min_probation_samples: int = 40):
        self.min_probation_samples = max(1, int(min_probation_samples))

    def build(
        self,
        review,
        *,
        target_layer: str,
        initial_weight: float | None = None,
        probation_samples: int | None = None,
        rollback_edge_r: float = 0.0,
        rollback_stop_first_rate: float = 0.50,
        rollback_direction_correct_rate: float = 0.50,
    ) -> ManualPromotionContract:
        payload = review.to_dict() if hasattr(review, "to_dict") else dict(review or {})
        state = str(payload.get("book_state", "") or "").upper().strip()
        recommendation = str(payload.get("recommendation", "") or "").upper().strip()
        if not state:
            raise ValueError("book_state is required")
        if recommendation != "ELIGIBLE_FOR_MANUAL_PROMOTION":
            raise PermissionError("manual promotion contract requires eligible RC20 review")

        target = str(target_layer or "").upper().strip()
        if target not in ALLOWED_TARGETS:
            raise ValueError("invalid target_layer")

        max_weight = MAX_INITIAL_WEIGHTS[target]
        weight = max_weight if initial_weight is None else float(initial_weight)
        if weight <= 0.0 or weight > max_weight:
            raise ValueError("initial_weight outside allowed range")

        probation = self.min_probation_samples if probation_samples is None else int(probation_samples)
        if probation < self.min_probation_samples:
            raise ValueError("probation_samples below minimum")
        if not 0.0 <= float(rollback_stop_first_rate) <= 1.0:
            raise ValueError("rollback_stop_first_rate must be between 0 and 1")
        if not 0.0 <= float(rollback_direction_correct_rate) <= 1.0:
            raise ValueError("rollback_direction_correct_rate must be between 0 and 1")

        reasons = [
            "SOURCE_SHADOW_REVIEW_APPROVED",
            "MANUAL_APPROVAL_REQUIRED",
            "RUNTIME_INACTIVE_BY_DEFAULT",
            "PROBATION_REQUIRED",
            "ROLLBACK_GUARDRAILS_REQUIRED",
        ]
        if target == "RISK":
            reasons.extend(("RISK_TARGET_EXCEPTIONAL", "RISK_WEIGHT_STRICTLY_CAPPED"))

        return ManualPromotionContract(
            version=self.VERSION,
            book_state=state,
            target_layer=target,
            initial_weight=round(weight, 4),
            probation_samples=probation,
            rollback_edge_r=round(float(rollback_edge_r), 4),
            rollback_stop_first_rate=round(float(rollback_stop_first_rate), 4),
            rollback_direction_correct_rate=round(float(rollback_direction_correct_rate), 4),
            source_recommendation=recommendation,
            manual_approval_required=True,
            runtime_active=False,
            status="DRAFT_FOR_MANUAL_APPROVAL",
            reasons=tuple(reasons),
        )

    @staticmethod
    def rollback_required(contract, metrics: dict) -> bool:
        payload = contract.to_dict() if hasattr(contract, "to_dict") else dict(contract or {})
        data = dict(metrics or {})
        completed = int(data.get("completed", 0) or 0)
        if completed < int(payload.get("probation_samples", 0) or 0):
            return False

        return bool(
            float(data.get("avg_edge_r", 0.0) or 0.0) < float(payload.get("rollback_edge_r", 0.0) or 0.0)
            or float(data.get("stop_first_rate", 0.0) or 0.0) > float(payload.get("rollback_stop_first_rate", 0.0) or 0.0)
            or float(data.get("direction_correct_rate", 0.0) or 0.0) < float(payload.get("rollback_direction_correct_rate", 0.0) or 0.0)
        )
