"""Comparador multi-pregao do A/B passivo de elegibilidade de microestrutura."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ScoreMicrostructureEligibilityABMultiSessionReport:
    classification: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    sessions: int = 0
    samples: int = 0
    weighted_average_delta: float = 0.0
    weighted_strong_candidate_rate: float = 0.0
    weighted_promising_rate: float = 0.0
    weighted_independent_strong_rate: float = 0.0
    weighted_correlated_rate: float = 0.0
    weighted_conflict_rate: float = 0.0
    weighted_grade_change_rate: float = 0.0
    weighted_validity_change_rate: float = 0.0
    weighted_average_confidence: float = 0.0
    delta_min: float = 0.0
    delta_max: float = 0.0
    delta_spread: float = 0.0
    strong_rate_spread: float = 0.0
    independent_strong_rate_spread: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreMicrostructureEligibilityABMultiSessionComparator:
    VERSION = "RC1-MICROSTRUCTURE-SCORE-AB-MULTI-SESSION"
    MIN_SESSIONS = 3
    MIN_SAMPLES = 300
    CONFLICT_LIMIT = 0.20
    MAX_DELTA_SPREAD = 0.75
    MAX_STRONG_RATE_SPREAD = 0.15
    MAX_INDEPENDENT_STRONG_RATE_SPREAD = 0.12
    STRONG_RATE = 0.15
    PROMISING_PLUS_STRONG_RATE = 0.35

    def compare(self, reports) -> ScoreMicrostructureEligibilityABMultiSessionReport:
        reports = [report for report in reports if getattr(report, "samples", 0) > 0]
        sessions = len(reports)
        samples = sum(int(report.samples) for report in reports)
        if sessions == 0:
            return ScoreMicrostructureEligibilityABMultiSessionReport(sessions=0, samples=0)

        weighted = lambda field: sum(float(getattr(r, field)) * r.samples for r in reports) / samples
        average_delta = weighted("average_delta")
        strong_rate = weighted("strong_candidate_rate")
        promising_rate = weighted("promising_rate")
        independent_strong_rate = weighted("independent_strong_rate")
        correlated_rate = weighted("correlated_rate")
        conflict_rate = weighted("conflict_rate")
        grade_change_rate = weighted("grade_change_rate")
        validity_change_rate = weighted("validity_change_rate")
        confidence = weighted("average_confidence")

        deltas = [float(r.average_delta) for r in reports]
        strong_rates = [float(r.strong_candidate_rate) for r in reports]
        independent_rates = [float(r.independent_strong_rate) for r in reports]
        delta_spread = max(deltas) - min(deltas)
        strong_spread = max(strong_rates) - min(strong_rates)
        independent_spread = max(independent_rates) - min(independent_rates)

        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            classification, recommendation = "INSUFFICIENT_DATA", "COLLECT_MORE_DATA"
        elif validity_change_rate > 0.0:
            classification, recommendation = "REVIEW_VALIDITY_CHANGES", "REVIEW_BEFORE_ENABLE"
        elif conflict_rate >= self.CONFLICT_LIMIT:
            classification, recommendation = "DEGRADED_BY_CONFLICT", "REVIEW_CONFLICTS"
        elif (delta_spread > self.MAX_DELTA_SPREAD
              or strong_spread > self.MAX_STRONG_RATE_SPREAD
              or independent_spread > self.MAX_INDEPENDENT_STRONG_RATE_SPREAD):
            classification, recommendation = "INCONSISTENT", "KEEP_OBSERVING"
        elif independent_strong_rate >= self.STRONG_RATE:
            classification, recommendation = "STABLE_STRONG", "KEEP_OBSERVING"
        elif strong_rate + promising_rate >= self.PROMISING_PLUS_STRONG_RATE:
            classification, recommendation = "STABLE_PROMISING", "KEEP_OBSERVING"
        else:
            classification, recommendation = "STABLE_WEAK", "KEEP_OBSERVING"

        return ScoreMicrostructureEligibilityABMultiSessionReport(
            classification=classification, recommendation=recommendation,
            sessions=sessions, samples=samples,
            weighted_average_delta=round(average_delta, 4),
            weighted_strong_candidate_rate=round(strong_rate, 4),
            weighted_promising_rate=round(promising_rate, 4),
            weighted_independent_strong_rate=round(independent_strong_rate, 4),
            weighted_correlated_rate=round(correlated_rate, 4),
            weighted_conflict_rate=round(conflict_rate, 4),
            weighted_grade_change_rate=round(grade_change_rate, 4),
            weighted_validity_change_rate=round(validity_change_rate, 4),
            weighted_average_confidence=round(confidence, 4),
            delta_min=round(min(deltas), 4), delta_max=round(max(deltas), 4),
            delta_spread=round(delta_spread, 4), strong_rate_spread=round(strong_spread, 4),
            independent_strong_rate_spread=round(independent_spread, 4), passive_only=True,
        )
