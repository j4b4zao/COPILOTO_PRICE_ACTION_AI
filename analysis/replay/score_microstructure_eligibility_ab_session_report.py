"""Relatório passivo por sessão do A/B de elegibilidade de microestrutura."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ScoreMicrostructureEligibilityABSessionReport:
    classification: str = "NO_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    samples: int = 0
    average_delta: float = 0.0
    strong_candidate_rate: float = 0.0
    promising_rate: float = 0.0
    independent_strong_rate: float = 0.0
    correlated_rate: float = 0.0
    conflict_rate: float = 0.0
    grade_change_rate: float = 0.0
    validity_change_rate: float = 0.0
    average_confidence: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreMicrostructureEligibilityABSessionReporter:
    VERSION = "RC1-MICROSTRUCTURE-SCORE-AB-SESSION-REPORT"
    MIN_SAMPLES = 100
    STRONG_RATE = 0.15
    PROMISING_PLUS_STRONG_RATE = 0.35
    CONFLICT_LIMIT = 0.20

    def build(self, recorder) -> ScoreMicrostructureEligibilityABSessionReport:
        samples = list(getattr(recorder, "samples", ()))
        total = len(samples)
        if total == 0:
            return ScoreMicrostructureEligibilityABSessionReport()

        strong = sum(s.eligibility_state == "STRONG_CANDIDATE" for s in samples)
        promising = sum(s.eligibility_state == "PROMISING" for s in samples)
        independent_strong = sum(
            s.eligibility_state == "STRONG_CANDIDATE"
            and s.correlation_bucket == "INDEPENDENT"
            and s.conflict_count == 0
            for s in samples
        )
        correlated = sum(s.correlated_evidence_count > 0 for s in samples)
        conflicts = sum(s.conflict_count > 0 for s in samples)
        grade_changes = sum(s.grade_changed for s in samples)
        validity_changes = sum(s.validity_changed for s in samples)
        strong_rate = strong / total
        promising_rate = promising / total
        independent_strong_rate = independent_strong / total
        conflict_rate = conflicts / total

        if conflict_rate >= self.CONFLICT_LIMIT:
            classification = "DEGRADED_BY_CONFLICT"
            recommendation = "REVIEW_CONFLICTS"
        elif total < self.MIN_SAMPLES:
            classification = "INSUFFICIENT_DATA"
            recommendation = "COLLECT_MORE_DATA"
        elif independent_strong_rate >= self.STRONG_RATE:
            classification = "STRONG_PASSIVE_SIGNAL"
            recommendation = "KEEP_OBSERVING"
        elif strong_rate + promising_rate >= self.PROMISING_PLUS_STRONG_RATE:
            classification = "PROMISING_PASSIVE_SIGNAL"
            recommendation = "KEEP_OBSERVING"
        else:
            classification = "WEAK_PASSIVE_SIGNAL"
            recommendation = "KEEP_OBSERVING"

        return ScoreMicrostructureEligibilityABSessionReport(
            classification=classification,
            recommendation=recommendation,
            samples=total,
            average_delta=round(sum(s.delta for s in samples) / total, 4),
            strong_candidate_rate=round(strong_rate, 4),
            promising_rate=round(promising_rate, 4),
            independent_strong_rate=round(independent_strong_rate, 4),
            correlated_rate=round(correlated / total, 4),
            conflict_rate=round(conflict_rate, 4),
            grade_change_rate=round(grade_changes / total, 4),
            validity_change_rate=round(validity_changes / total, 4),
            average_confidence=round(sum(s.confidence for s in samples) / total, 4),
            passive_only=True,
        )
