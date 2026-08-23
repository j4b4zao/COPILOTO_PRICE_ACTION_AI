"""Comparador multi-sessão passivo da elegibilidade de microestrutura."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.microstructure_eligibility_session_report import (
    MicrostructureEligibilitySessionReport,
)


@dataclass(slots=True, frozen=True)
class MicrostructureEligibilityMultiSessionReport:
    sessions: int = 0
    samples: int = 0
    weighted_not_eligible_rate: float = 0.0
    weighted_observable_rate: float = 0.0
    weighted_promising_rate: float = 0.0
    weighted_strong_candidate_rate: float = 0.0
    weighted_eligible_rate: float = 0.0
    weighted_conflict_rate: float = 0.0
    weighted_correlation_rate: float = 0.0
    weighted_average_confidence: float = 0.0
    min_strong_candidate_rate: float = 0.0
    max_strong_candidate_rate: float = 0.0
    strong_candidate_spread: float = 0.0
    min_eligible_rate: float = 0.0
    max_eligible_rate: float = 0.0
    eligible_rate_spread: float = 0.0
    strong_sessions: int = 0
    promising_sessions: int = 0
    weak_sessions: int = 0
    degraded_sessions: int = 0
    no_data_sessions: int = 0
    stability: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureEligibilityMultiSessionComparator:
    VERSION = "RC1-MICROSTRUCTURE-ELIGIBILITY-MULTI-SESSION"
    MIN_SESSIONS = 3
    MIN_SAMPLES = 300
    MAX_STRONG_SPREAD = 0.10
    MAX_ELIGIBLE_SPREAD = 0.15
    MAX_CONFLICT_RATE = 0.20

    def compare(self, reports) -> MicrostructureEligibilityMultiSessionReport:
        reports = list(reports)
        if not all(isinstance(report, MicrostructureEligibilitySessionReport) for report in reports):
            raise TypeError("Todos os relatórios devem ser MicrostructureEligibilitySessionReport.")

        valid = [report for report in reports if report.samples > 0]
        total_samples = sum(report.samples for report in valid)
        session_count = len(valid)

        if not valid:
            return MicrostructureEligibilityMultiSessionReport()

        weighted_not = self._weighted(valid, "not_eligible_rate", total_samples)
        weighted_observable = self._weighted(valid, "observable_rate", total_samples)
        weighted_promising = self._weighted(valid, "promising_rate", total_samples)
        weighted_strong = self._weighted(valid, "strong_candidate_rate", total_samples)
        weighted_conflict = self._weighted(valid, "conflict_rate", total_samples)
        weighted_correlation = self._weighted(valid, "correlation_rate", total_samples)
        weighted_confidence = self._weighted(valid, "average_confidence", total_samples)
        weighted_eligible = weighted_promising + weighted_strong

        strong_rates = [float(report.strong_candidate_rate) for report in valid]
        eligible_rates = [float(report.promising_rate) + float(report.strong_candidate_rate) for report in valid]
        min_strong = min(strong_rates)
        max_strong = max(strong_rates)
        min_eligible = min(eligible_rates)
        max_eligible = max(eligible_rates)
        strong_spread = max_strong - min_strong
        eligible_spread = max_eligible - min_eligible

        state_counts = {
            "STRONG_ELIGIBILITY_SIGNAL": 0,
            "PROMISING_ELIGIBILITY_SIGNAL": 0,
            "WEAK_ELIGIBILITY_SIGNAL": 0,
            "DEGRADED_BY_CONFLICT": 0,
            "NO_DATA": len(reports) - len(valid),
        }
        for report in valid:
            if report.session_state in state_counts:
                state_counts[report.session_state] += 1

        if session_count < self.MIN_SESSIONS or total_samples < self.MIN_SAMPLES:
            stability = "INSUFFICIENT_DATA"
            recommendation = "COLLECT_MORE_DATA"
        elif weighted_conflict >= self.MAX_CONFLICT_RATE:
            stability = "DEGRADED_BY_CONFLICT"
            recommendation = "REVIEW_CONFLICTS"
        elif strong_spread > self.MAX_STRONG_SPREAD or eligible_spread > self.MAX_ELIGIBLE_SPREAD:
            stability = "INCONSISTENT"
            recommendation = "REVIEW_STABILITY"
        elif weighted_strong >= 0.10 and weighted_eligible >= 0.30 and weighted_conflict <= 0.10 and weighted_correlation <= 0.30:
            stability = "STABLE_STRONG"
            recommendation = "KEEP_OBSERVING"
        elif weighted_eligible >= 0.20:
            stability = "STABLE_PROMISING"
            recommendation = "KEEP_OBSERVING"
        else:
            stability = "STABLE_WEAK"
            recommendation = "KEEP_OBSERVING"

        return MicrostructureEligibilityMultiSessionReport(
            sessions=session_count,
            samples=total_samples,
            weighted_not_eligible_rate=round(weighted_not, 4),
            weighted_observable_rate=round(weighted_observable, 4),
            weighted_promising_rate=round(weighted_promising, 4),
            weighted_strong_candidate_rate=round(weighted_strong, 4),
            weighted_eligible_rate=round(weighted_eligible, 4),
            weighted_conflict_rate=round(weighted_conflict, 4),
            weighted_correlation_rate=round(weighted_correlation, 4),
            weighted_average_confidence=round(weighted_confidence, 4),
            min_strong_candidate_rate=round(min_strong, 4),
            max_strong_candidate_rate=round(max_strong, 4),
            strong_candidate_spread=round(strong_spread, 4),
            min_eligible_rate=round(min_eligible, 4),
            max_eligible_rate=round(max_eligible, 4),
            eligible_rate_spread=round(eligible_spread, 4),
            strong_sessions=state_counts["STRONG_ELIGIBILITY_SIGNAL"],
            promising_sessions=state_counts["PROMISING_ELIGIBILITY_SIGNAL"],
            weak_sessions=state_counts["WEAK_ELIGIBILITY_SIGNAL"],
            degraded_sessions=state_counts["DEGRADED_BY_CONFLICT"],
            no_data_sessions=state_counts["NO_DATA"],
            stability=stability,
            recommendation=recommendation,
            passive_only=True,
        )

    @staticmethod
    def _weighted(reports, field: str, total_samples: int) -> float:
        if total_samples <= 0:
            return 0.0
        return sum(float(getattr(report, field)) * report.samples for report in reports) / total_samples
