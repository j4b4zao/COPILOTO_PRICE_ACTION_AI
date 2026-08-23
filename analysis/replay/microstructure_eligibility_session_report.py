"""Relatório passivo por sessão da elegibilidade de microestrutura."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class MicrostructureEligibilitySessionReport:
    samples: int = 0
    not_eligible_rate: float = 0.0
    observable_rate: float = 0.0
    promising_rate: float = 0.0
    strong_candidate_rate: float = 0.0
    conflict_rate: float = 0.0
    correlation_rate: float = 0.0
    average_confidence: float = 0.0
    session_state: str = "NO_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureEligibilitySessionReporter:
    VERSION = "RC1-MICROSTRUCTURE-ELIGIBILITY-SESSION-REPORT"
    MIN_SAMPLES = 100

    def build(self, recorder) -> MicrostructureEligibilitySessionReport:
        summary = recorder.summary()
        rates = recorder.rates()
        total = int(summary.get("samples", 0))
        if total <= 0:
            return MicrostructureEligibilitySessionReport()

        promising = float(rates["promising_rate"])
        strong = float(rates["strong_candidate_rate"])
        conflicts = float(rates["conflict_rate"])
        correlation = float(rates["correlation_rate"])

        if conflicts >= 0.25:
            state = "DEGRADED_BY_CONFLICT"
        elif strong >= 0.10 and promising + strong >= 0.30 and correlation <= 0.30:
            state = "STRONG_ELIGIBILITY_SIGNAL"
        elif promising + strong >= 0.20:
            state = "PROMISING_ELIGIBILITY_SIGNAL"
        else:
            state = "WEAK_ELIGIBILITY_SIGNAL"

        recommendation = "COLLECT_MORE_DATA" if total < self.MIN_SAMPLES else "KEEP_OBSERVING"
        if total >= self.MIN_SAMPLES and conflicts >= 0.25:
            recommendation = "REVIEW_CONFLICTS"

        return MicrostructureEligibilitySessionReport(
            samples=total,
            not_eligible_rate=float(rates["not_eligible_rate"]),
            observable_rate=float(rates["observable_rate"]),
            promising_rate=promising,
            strong_candidate_rate=strong,
            conflict_rate=conflicts,
            correlation_rate=correlation,
            average_confidence=float(summary.get("average_confidence", 0.0)),
            session_state=state,
            recommendation=recommendation,
            passive_only=True,
        )
