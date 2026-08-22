"""
analysis/replay/book_diagnostics_promotion_gate.py

BookDiagnostics RC12 - Promotion Gate.

Converte métricas offline do Outcome Analyzer em uma decisão de governança:
- REJECTED
- KEEP_OBSERVING
- CANDIDATE_FOR_PROMOTION

Importante:
- nunca promove automaticamente um diagnóstico para Score/Risk/Decision;
- apenas classifica evidência experimental;
- promoção real continua exigindo revisão humana e validação fora da amostra.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class PromotionGateResult:
    status: str = "KEEP_OBSERVING"
    eligible: bool = False
    sample_count: int = 0
    edge_r: float = 0.0
    target_first_rate: float = 0.0
    stop_first_rate: float = 0.0
    future_alignment_rate: float = 0.0
    stable_sessions: int = 0
    total_sessions: int = 0
    stability_rate: float = 0.0
    score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsPromotionGate:
    """Objective, passive promotion gate for BookDiagnostics research."""

    VERSION = "RC12-PROMOTION-GATE"

    def __init__(
        self,
        min_samples: int = 30,
        promotion_samples: int = 60,
        min_edge_r: float = 0.20,
        min_target_first_rate: float = 0.55,
        max_stop_first_rate: float = 0.40,
        min_future_alignment_rate: float = 0.55,
        min_sessions: int = 3,
        min_stability_rate: float = 0.67,
    ):
        self.min_samples = max(1, int(min_samples))
        self.promotion_samples = max(self.min_samples, int(promotion_samples))
        self.min_edge_r = float(min_edge_r)
        self.min_target_first_rate = float(min_target_first_rate)
        self.max_stop_first_rate = float(max_stop_first_rate)
        self.min_future_alignment_rate = float(min_future_alignment_rate)
        self.min_sessions = max(1, int(min_sessions))
        self.min_stability_rate = float(min_stability_rate)

    def evaluate(self, metrics: dict, session_metrics=None) -> PromotionGateResult:
        metrics = dict(metrics or {})
        sessions = [dict(item or {}) for item in (session_metrics or [])]

        samples = int(metrics.get("directional_samples", metrics.get("samples", 0)) or 0)
        edge_r = float(metrics.get("edge_r", 0.0) or 0.0)
        target_rate = float(metrics.get("book_target_first_rate", 0.0) or 0.0)
        stop_rate = float(metrics.get("book_stop_first_rate", 0.0) or 0.0)
        future_rate = float(metrics.get("future_direction_alignment_rate", 0.0) or 0.0)

        stable_sessions = sum(self._session_is_stable(item) for item in sessions)
        total_sessions = len(sessions)
        stability_rate = (
            stable_sessions / total_sessions
            if total_sessions
            else 0.0
        )

        reasons: list[str] = []

        if samples < self.min_samples:
            reasons.append("INSUFFICIENT_SAMPLE")

        if edge_r <= 0.0 and samples >= self.min_samples:
            reasons.append("NON_POSITIVE_EDGE")
        elif edge_r < self.min_edge_r:
            reasons.append("EDGE_BELOW_PROMOTION_THRESHOLD")

        if target_rate < 0.50 and samples >= self.min_samples:
            reasons.append("TARGET_FIRST_RATE_WEAK")
        elif target_rate < self.min_target_first_rate:
            reasons.append("TARGET_FIRST_RATE_BELOW_PROMOTION_THRESHOLD")

        if stop_rate > 0.50 and samples >= self.min_samples:
            reasons.append("STOP_FIRST_RATE_TOO_HIGH")
        elif stop_rate > self.max_stop_first_rate:
            reasons.append("STOP_FIRST_RATE_ABOVE_PROMOTION_THRESHOLD")

        if future_rate < 0.50 and samples >= self.min_samples:
            reasons.append("FUTURE_ALIGNMENT_WEAK")
        elif future_rate < self.min_future_alignment_rate:
            reasons.append("FUTURE_ALIGNMENT_BELOW_PROMOTION_THRESHOLD")

        if total_sessions < self.min_sessions:
            reasons.append("INSUFFICIENT_SESSION_COVERAGE")
        elif stability_rate < self.min_stability_rate:
            reasons.append("SESSION_STABILITY_BELOW_THRESHOLD")

        hard_reject = bool(
            samples >= self.min_samples
            and (
                edge_r <= 0.0
                or target_rate < 0.50
                or stop_rate > 0.50
                or future_rate < 0.50
            )
        )

        candidate = bool(
            samples >= self.promotion_samples
            and edge_r >= self.min_edge_r
            and target_rate >= self.min_target_first_rate
            and stop_rate <= self.max_stop_first_rate
            and future_rate >= self.min_future_alignment_rate
            and total_sessions >= self.min_sessions
            and stability_rate >= self.min_stability_rate
        )

        if hard_reject:
            status = "REJECTED"
            eligible = False
        elif candidate:
            status = "CANDIDATE_FOR_PROMOTION"
            eligible = True
            reasons.append("PROMOTION_THRESHOLDS_MET")
            reasons.append("MANUAL_REVIEW_REQUIRED")
            reasons.append("OUT_OF_SAMPLE_VALIDATION_REQUIRED")
        else:
            status = "KEEP_OBSERVING"
            eligible = False

        score = self._score(
            samples=samples,
            edge_r=edge_r,
            target_rate=target_rate,
            stop_rate=stop_rate,
            future_rate=future_rate,
            stability_rate=stability_rate,
        )

        return PromotionGateResult(
            status=status,
            eligible=eligible,
            sample_count=samples,
            edge_r=round(edge_r, 4),
            target_first_rate=round(target_rate, 4),
            stop_first_rate=round(stop_rate, 4),
            future_alignment_rate=round(future_rate, 4),
            stable_sessions=stable_sessions,
            total_sessions=total_sessions,
            stability_rate=round(stability_rate, 4),
            score=score,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def _session_is_stable(self, metrics: dict) -> bool:
        samples = int(metrics.get("directional_samples", metrics.get("samples", 0)) or 0)
        if samples <= 0:
            return False
        return bool(
            float(metrics.get("edge_r", 0.0) or 0.0) > 0.0
            and float(metrics.get("book_target_first_rate", 0.0) or 0.0) >= 0.50
            and float(metrics.get("book_stop_first_rate", 0.0) or 0.0) <= 0.50
        )

    def _score(
        self,
        *,
        samples: int,
        edge_r: float,
        target_rate: float,
        stop_rate: float,
        future_rate: float,
        stability_rate: float,
    ) -> float:
        sample_score = min(20.0, 20.0 * samples / self.promotion_samples)
        edge_score = min(25.0, max(0.0, 25.0 * edge_r / max(self.min_edge_r, 0.0001)))
        target_score = min(20.0, max(0.0, target_rate * 20.0))
        stop_score = min(15.0, max(0.0, (1.0 - stop_rate) * 15.0))
        future_score = min(10.0, max(0.0, future_rate * 10.0))
        stability_score = min(10.0, max(0.0, stability_rate * 10.0))
        return round(
            min(
                100.0,
                sample_score
                + edge_score
                + target_score
                + stop_score
                + future_score
                + stability_score,
            ),
            2,
        )
