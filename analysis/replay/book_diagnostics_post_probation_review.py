"""
BookDiagnostics RC24 - Post-Probation Review.

Avalia formalmente o resultado da probation RC23 e produz uma recomendacao
de governanca. Nenhuma promocao e aplicada automaticamente ao runtime.

Recomendacoes possiveis:
- PROMOTE
- EXTEND_PROBATION
- ROLLBACK
- RETURN_TO_RESEARCH
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_manual_promotion_contract import (
    BookDiagnosticsManualPromotionContractBuilder,
)


@dataclass(slots=True, frozen=True)
class PostProbationReview:
    version: str
    book_state: str
    target_layer: str
    recommendation: str
    completed_samples: int
    probation_samples: int
    avg_edge_r: float
    stop_first_rate: float
    direction_correct_rate: float
    manual_approval_required: bool
    runtime_active: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsPostProbationReviewer:
    VERSION = "RC24-POST-PROBATION-REVIEW"

    def __init__(
        self,
        *,
        promote_edge_margin: float = 0.10,
        promote_stop_margin: float = 0.05,
        promote_direction_margin: float = 0.05,
    ):
        self.promote_edge_margin = float(promote_edge_margin)
        self.promote_stop_margin = float(promote_stop_margin)
        self.promote_direction_margin = float(promote_direction_margin)

    def evaluate(self, runtime_state, contract, metrics: dict) -> PostProbationReview:
        state = runtime_state.to_dict() if hasattr(runtime_state, "to_dict") else dict(runtime_state or {})
        contract_data = contract.to_dict() if hasattr(contract, "to_dict") else dict(contract or {})
        data = dict(metrics or {})

        book_state = str(state.get("book_state", "") or "").upper().strip()
        target_layer = str(state.get("target_layer", "") or "").upper().strip()
        contract_state = str(contract_data.get("book_state", "") or "").upper().strip()
        contract_target = str(contract_data.get("target_layer", "") or "").upper().strip()
        if not book_state or book_state != contract_state:
            raise ValueError("runtime state does not match promotion contract")
        if target_layer != contract_target:
            raise ValueError("runtime target does not match promotion contract")

        status = str(state.get("status", "") or "").upper().strip()
        if bool(state.get("runtime_active", False)) and status != "PROBATION_ACTIVE":
            raise ValueError("invalid runtime state")

        probation_samples = int(contract_data.get("probation_samples", 0) or 0)
        completed = int(data.get("completed", state.get("samples_seen", 0)) or 0)
        edge_r = float(data.get("avg_edge_r", 0.0) or 0.0)
        stop_rate = float(data.get("stop_first_rate", 0.0) or 0.0)
        direction_rate = float(data.get("direction_correct_rate", 0.0) or 0.0)

        rollback_required = BookDiagnosticsManualPromotionContractBuilder.rollback_required(
            contract,
            data,
        )
        reasons: list[str] = []

        if status == "ROLLED_BACK" or bool(state.get("rollback_triggered", False)) or rollback_required:
            recommendation = "ROLLBACK"
            reasons.append("PROBATION_GUARDRAIL_FAILURE")
        elif status == "PROBATION_STOPPED_MANUALLY":
            recommendation = "RETURN_TO_RESEARCH"
            reasons.append("PROBATION_STOPPED_MANUALLY")
        elif completed < probation_samples:
            recommendation = "EXTEND_PROBATION"
            reasons.append("PROBATION_SAMPLE_NOT_COMPLETE")
        else:
            rollback_edge = float(contract_data.get("rollback_edge_r", 0.0) or 0.0)
            rollback_stop = float(contract_data.get("rollback_stop_first_rate", 0.50) or 0.50)
            rollback_direction = float(contract_data.get("rollback_direction_correct_rate", 0.50) or 0.50)

            strong_edge = edge_r >= rollback_edge + self.promote_edge_margin
            strong_stop = stop_rate <= max(0.0, rollback_stop - self.promote_stop_margin)
            strong_direction = direction_rate >= min(1.0, rollback_direction + self.promote_direction_margin)

            if strong_edge and strong_stop and strong_direction:
                recommendation = "PROMOTE"
                reasons.extend((
                    "PROBATION_SAMPLE_COMPLETE",
                    "PROBATION_EDGE_CONFIRMED",
                    "PROBATION_STOP_RATE_CONFIRMED",
                    "PROBATION_DIRECTIONAL_ACCURACY_CONFIRMED",
                    "FINAL_MANUAL_APPROVAL_REQUIRED",
                    "NO_AUTOMATIC_RUNTIME_PROMOTION",
                ))
            elif edge_r >= rollback_edge and stop_rate <= rollback_stop and direction_rate >= rollback_direction:
                recommendation = "EXTEND_PROBATION"
                reasons.append("PROBATION_SAFE_BUT_PROMOTION_MARGIN_NOT_REACHED")
            else:
                recommendation = "RETURN_TO_RESEARCH"
                reasons.append("PROBATION_QUALITY_INCONCLUSIVE")

        return PostProbationReview(
            version=self.VERSION,
            book_state=book_state,
            target_layer=target_layer,
            recommendation=recommendation,
            completed_samples=completed,
            probation_samples=probation_samples,
            avg_edge_r=round(edge_r, 4),
            stop_first_rate=round(stop_rate, 4),
            direction_correct_rate=round(direction_rate, 4),
            manual_approval_required=(recommendation == "PROMOTE"),
            runtime_active=False,
            reasons=tuple(dict.fromkeys(reasons)),
        )
