"""
analysis/replay/book_diagnostics_shadow_promotion_review.py

BookDiagnostics RC20 - Shadow Promotion Review.

Avalia metricas reais do Shadow Mode RC19 e produz uma recomendacao formal
de governanca para candidatos ja aprovados para shadow.

Resultados possiveis:
- KEEP_SHADOW
- RETURN_TO_RESEARCH
- REJECT_CANDIDATE
- ELIGIBLE_FOR_MANUAL_PROMOTION

Importante:
- nenhuma transicao e aplicada automaticamente ao Candidate Registry;
- promocao continua exigindo revisao humana explicita;
- a camada nao altera AnalysisContext, Strategy, Score, Risk, Decision ou Alert.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ShadowPromotionReview:
    version: str
    book_state: str
    recommendation: str
    completed_samples: int
    target_first_rate: float
    stop_first_rate: float
    direction_correct_rate: float
    avg_mfe_r: float
    avg_mae_r: float
    avg_edge_r: float
    manual_review_required: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsShadowPromotionReviewer:
    VERSION = "RC20-SHADOW-PROMOTION-REVIEW"

    def __init__(
        self,
        *,
        min_samples: int = 30,
        promotion_samples: int = 80,
        min_target_first_rate: float = 0.55,
        max_stop_first_rate: float = 0.40,
        min_direction_correct_rate: float = 0.55,
        min_edge_r: float = 0.20,
        reject_edge_r: float = -0.10,
        reject_stop_first_rate: float = 0.60,
    ):
        self.min_samples = max(1, int(min_samples))
        self.promotion_samples = max(self.min_samples, int(promotion_samples))
        self.min_target_first_rate = float(min_target_first_rate)
        self.max_stop_first_rate = float(max_stop_first_rate)
        self.min_direction_correct_rate = float(min_direction_correct_rate)
        self.min_edge_r = float(min_edge_r)
        self.reject_edge_r = float(reject_edge_r)
        self.reject_stop_first_rate = float(reject_stop_first_rate)

    def evaluate(self, metrics: dict, *, registry_record=None) -> ShadowPromotionReview:
        data = dict(metrics or {})
        state = str(data.get("book_state", "") or "").upper().strip()
        if not state:
            raise ValueError("book_state is required in shadow metrics")

        if registry_record is not None:
            record_state = str(getattr(registry_record, "book_state", "") or "").upper().strip()
            status = str(getattr(registry_record, "status", "") or "").upper().strip()
            if record_state and record_state != state:
                raise ValueError("registry record does not match shadow metrics state")
            if status != "APPROVED_FOR_SHADOW":
                raise PermissionError("candidate must be APPROVED_FOR_SHADOW for RC20 review")

        completed = int(data.get("completed", 0) or 0)
        target_rate = float(data.get("target_first_rate", 0.0) or 0.0)
        stop_rate = float(data.get("stop_first_rate", 0.0) or 0.0)
        direction_rate = float(data.get("direction_correct_rate", 0.0) or 0.0)
        mfe_r = float(data.get("avg_mfe_r", 0.0) or 0.0)
        mae_r = float(data.get("avg_mae_r", 0.0) or 0.0)
        edge_r = float(data.get("avg_edge_r", 0.0) or 0.0)

        reasons = []

        if completed < self.min_samples:
            recommendation = "KEEP_SHADOW"
            reasons.append("SHADOW_SAMPLE_TOO_SMALL")
        elif edge_r <= self.reject_edge_r:
            recommendation = "REJECT_CANDIDATE"
            reasons.append("NEGATIVE_SHADOW_EDGE")
        elif stop_rate >= self.reject_stop_first_rate:
            recommendation = "REJECT_CANDIDATE"
            reasons.append("EXCESSIVE_SHADOW_STOP_RATE")
        else:
            quality_pass = bool(
                target_rate >= self.min_target_first_rate
                and stop_rate <= self.max_stop_first_rate
                and direction_rate >= self.min_direction_correct_rate
                and edge_r >= self.min_edge_r
            )

            if quality_pass and completed >= self.promotion_samples:
                recommendation = "ELIGIBLE_FOR_MANUAL_PROMOTION"
                reasons.extend((
                    "SHADOW_SAMPLE_SUFFICIENT",
                    "SHADOW_EDGE_CONFIRMED",
                    "SHADOW_TARGET_RATE_CONFIRMED",
                    "SHADOW_STOP_RATE_CONTROLLED",
                    "SHADOW_DIRECTIONAL_ACCURACY_CONFIRMED",
                    "MANUAL_PROMOTION_REVIEW_REQUIRED",
                    "NO_AUTOMATIC_RUNTIME_PROMOTION",
                ))
            elif quality_pass:
                recommendation = "KEEP_SHADOW"
                reasons.append("QUALITY_CONFIRMED_BUT_PROMOTION_SAMPLE_NOT_REACHED")
            else:
                recommendation = "RETURN_TO_RESEARCH"
                if target_rate < self.min_target_first_rate:
                    reasons.append("SHADOW_TARGET_RATE_BELOW_THRESHOLD")
                if stop_rate > self.max_stop_first_rate:
                    reasons.append("SHADOW_STOP_RATE_ABOVE_THRESHOLD")
                if direction_rate < self.min_direction_correct_rate:
                    reasons.append("SHADOW_DIRECTIONAL_ACCURACY_BELOW_THRESHOLD")
                if edge_r < self.min_edge_r:
                    reasons.append("SHADOW_EDGE_BELOW_THRESHOLD")

        return ShadowPromotionReview(
            version=self.VERSION,
            book_state=state,
            recommendation=recommendation,
            completed_samples=completed,
            target_first_rate=round(target_rate, 4),
            stop_first_rate=round(stop_rate, 4),
            direction_correct_rate=round(direction_rate, 4),
            avg_mfe_r=round(mfe_r, 4),
            avg_mae_r=round(mae_r, 4),
            avg_edge_r=round(edge_r, 4),
            manual_review_required=(recommendation == "ELIGIBLE_FOR_MANUAL_PROMOTION"),
            reasons=tuple(dict.fromkeys(reasons)),
        )
