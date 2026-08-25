"""
analysis/replay/book_diagnostics_evidence_report.py

BookDiagnostics RC16 - Promotion Evidence Report.

Reune em uma ficha auditavel as evidencias necessarias antes de qualquer
promocao manual de um estado experimental dos livros:
- outcome geral;
- estabilidade por sessao;
- estabilidade por regime;
- walk-forward fora da amostra;
- Promotion Gate RC12.

A camada e estritamente offline/passiva e nao altera runtime.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.book_diagnostics_outcome_analyzer import BookDiagnosticsOutcomeAnalyzer
from analysis.replay.book_diagnostics_promotion_gate import BookDiagnosticsPromotionGate
from analysis.replay.book_diagnostics_regime_segmenter import BookDiagnosticsRegimeSegmenter
from analysis.replay.book_diagnostics_session_analyzer import BookDiagnosticsSessionAnalyzer
from analysis.replay.book_diagnostics_walk_forward import BookDiagnosticsWalkForward


@dataclass(slots=True, frozen=True)
class PromotionEvidenceReport:
    version: str
    book_state: str
    sample_count: int
    overall_metrics: dict
    session_metrics: tuple[dict, ...]
    regime_metrics: tuple[dict, ...]
    walk_forward: dict
    promotion_gate: dict
    evidence_status: str
    ready_for_manual_review: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


class BookDiagnosticsEvidenceReporter:
    VERSION = "RC16-PROMOTION-EVIDENCE-REPORT"

    def __init__(self, gate=None, walk_forward=None):
        self.analyzer = BookDiagnosticsOutcomeAnalyzer()
        self.session_analyzer = BookDiagnosticsSessionAnalyzer()
        self.regime_segmenter = BookDiagnosticsRegimeSegmenter(self.analyzer)
        self.gate = gate or BookDiagnosticsPromotionGate()
        self.walk_forward = walk_forward or BookDiagnosticsWalkForward()

    def build(self, paired_records, *, book_state: str, enriched_records=None) -> PromotionEvidenceReport:
        state = str(book_state or "").upper().strip()
        filtered = self._filter_state(paired_records, state)
        overall = self.analyzer.analyze(filtered)["overall"]
        sessions = self.session_analyzer.promotion_session_metrics(
            filtered,
            book_state=state,
        )
        gate_result = self.gate.evaluate(overall, sessions).to_dict()
        walk = self.walk_forward.evaluate_state(filtered, state)

        regimes = []
        if enriched_records is not None:
            enriched_filtered = self._filter_enriched_state(enriched_records, state)
            regimes = self.regime_segmenter.promotion_regime_metrics(enriched_filtered)

        reasons = []
        if gate_result["status"] != "CANDIDATE_FOR_PROMOTION":
            reasons.append("PROMOTION_GATE_NOT_PASSED")
        if not walk.get("walk_forward_stable", False):
            reasons.append("OUT_OF_SAMPLE_NOT_STABLE")
        if not regimes:
            reasons.append("REGIME_EVIDENCE_NOT_AVAILABLE")
        elif not self._regimes_stable(regimes):
            reasons.append("REGIME_STABILITY_NOT_CONFIRMED")

        ready = bool(
            gate_result["status"] == "CANDIDATE_FOR_PROMOTION"
            and walk.get("walk_forward_stable", False)
            and regimes
            and self._regimes_stable(regimes)
        )

        if ready:
            status = "READY_FOR_MANUAL_REVIEW"
            reasons.extend((
                "ALL_EVIDENCE_GATES_PASSED",
                "MANUAL_REVIEW_REQUIRED",
                "NO_AUTOMATIC_RUNTIME_PROMOTION",
            ))
        elif int(overall.get("directional_samples", 0) or 0) == 0:
            status = "INSUFFICIENT_EVIDENCE"
            reasons.append("NO_DIRECTIONAL_OUTCOMES")
        else:
            status = "KEEP_RESEARCHING"

        return PromotionEvidenceReport(
            version=self.VERSION,
            book_state=state,
            sample_count=int(overall.get("directional_samples", 0) or 0),
            overall_metrics=dict(overall),
            session_metrics=tuple(sessions),
            regime_metrics=tuple(regimes),
            walk_forward=dict(walk),
            promotion_gate=dict(gate_result),
            evidence_status=status,
            ready_for_manual_review=ready,
            reasons=tuple(dict.fromkeys(reasons)),
        )

    def _filter_state(self, records, state):
        filtered = []
        for record in records or []:
            sample, _outcome = self.analyzer._split(record)
            if str(getattr(sample, "book_state", "") or "").upper() == state:
                filtered.append(record)
        return filtered

    def _filter_enriched_state(self, records, state):
        filtered = []
        for record in records or []:
            sample, _outcome, _meta = self.regime_segmenter._split(record)
            if str(getattr(sample, "book_state", "") or "").upper() == state:
                filtered.append(record)
        return filtered

    @staticmethod
    def _regimes_stable(regime_metrics) -> bool:
        usable = [row for row in regime_metrics if row.get("regime") != "UNKNOWN"]
        if not usable:
            return False
        return all(
            float(row.get("edge_r", 0.0) or 0.0) > 0.0
            and float(row.get("book_target_first_rate", 0.0) or 0.0) >= 0.50
            and float(row.get("book_stop_first_rate", 0.0) or 0.0) <= 0.50
            for row in usable
        )
