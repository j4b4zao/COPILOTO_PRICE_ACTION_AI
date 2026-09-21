"""Comparacao descritiva e passiva de cohorts de microestrutura.

Deltas representam prospectivo menos historico, sem inferencia de desempenho,
equivalencia ou aprovacao. O denominador prospectivo e a quantidade de samples
individuais capturados, nao a quantidade de ciclos da sessao.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any


VERSION = "RC1-HISTORICAL-PROSPECTIVE-MICROSTRUCTURE-COMPARISON"


@dataclass(slots=True, frozen=True)
class HistoricalProspectiveMicrostructureComparisonReport:
    historical_samples: int
    prospective_samples: int
    historical_confirmed_rate: float
    prospective_confirmed_rate: float
    historical_conflict_rate: float
    prospective_conflict_rate: float
    historical_insufficient_rate: float
    prospective_insufficient_rate: float
    historical_two_or_more_independent_rate: float
    prospective_two_or_more_independent_rate: float
    historical_correlated_rate: float
    prospective_correlated_rate: float
    prospective_high_quality_rate: float
    prospective_three_source_rate: float
    prospective_average_confidence: float
    confirmed_rate_delta: float
    conflict_rate_delta: float
    insufficient_rate_delta: float
    two_or_more_independent_rate_delta: float
    correlated_rate_delta: float
    historical_cohort_label: str
    prospective_cohort_label: str
    version: str = field(default=VERSION, init=False)
    status: str = field(default="DESCRIPTIVE_ONLY", init=False)
    research_only: bool = field(default=True, init=False)
    observational_only: bool = field(default=True, init=False)
    predictive_claim_allowed: bool = field(default=False, init=False)
    score_influence_allowed: bool = field(default=False, init=False)
    risk_influence_allowed: bool = field(default=False, init=False)
    decision_influence_allowed: bool = field(default=False, init=False)
    alert_influence_allowed: bool = field(default=False, init=False)
    order_execution_allowed: bool = field(default=False, init=False)
    promotion_allowed: bool = field(default=False, init=False)

    def to_dict(self) -> dict:
        return asdict(self)


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _rate(count: int, samples: int) -> float:
    return count / samples if samples else 0.0


def _evidence_count(distribution: Mapping, minimum: int) -> int:
    return sum(int(count) for key, count in distribution.items() if int(key) >= minimum)


class HistoricalProspectiveMicrostructureComparator:
    VERSION = VERSION

    def compare(
        self,
        historical_report,
        prospective_report,
        *,
        historical_cohort_label: str = "HISTORICAL",
        prospective_cohort_label: str = "PROSPECTIVE",
    ) -> HistoricalProspectiveMicrostructureComparisonReport:
        """Accept report objects or mappings, including the prospective block alone."""
        evidence = _get(prospective_report, "prospective_microstructure", prospective_report)
        samples = list(_get(evidence, "samples", ()))
        aggregate = _get(evidence, "report", {})
        historical_samples = int(_get(historical_report, "samples", 0))
        prospective_samples = len(samples)

        historical_counts = {
            "confirmed": int(_get(historical_report, "confirmed", 0)),
            "conflict": int(_get(historical_report, "conflict", 0)),
            "insufficient": int(_get(historical_report, "insufficient_data", 0)),
            "two_or_more_independent": _evidence_count(
                _get(historical_report, "independent_evidence", {}), 2
            ),
            "correlated": _evidence_count(
                _get(historical_report, "correlated_evidence", {}), 1
            ),
        }
        prospective_counts = {
            "confirmed": sum(_get(s, "state") == "CONFIRMED" for s in samples),
            "conflict": sum(_get(s, "state") == "CONFLICT" for s in samples),
            "insufficient": sum(_get(s, "state") == "INSUFFICIENT_DATA" for s in samples),
            "two_or_more_independent": sum(
                int(_get(s, "independent_evidence_count", 0)) >= 2 for s in samples
            ),
            "correlated": sum(
                int(_get(s, "correlated_evidence_count", 0)) >= 1 for s in samples
            ),
        }
        metrics = {}
        for name, count in historical_counts.items():
            historical_rate = _rate(count, historical_samples)
            prospective_rate = _rate(prospective_counts[name], prospective_samples)
            metrics[f"historical_{name}_rate"] = round(historical_rate, 4)
            metrics[f"prospective_{name}_rate"] = round(prospective_rate, 4)
            metrics[f"{name}_rate_delta"] = round(prospective_rate - historical_rate, 4)

        for name in ("high_quality_rate", "three_source_rate", "average_confidence"):
            metrics[f"prospective_{name}"] = round(float(_get(aggregate, name, 0.0)), 4)

        return HistoricalProspectiveMicrostructureComparisonReport(
            historical_samples=historical_samples,
            prospective_samples=prospective_samples,
            historical_cohort_label=historical_cohort_label,
            prospective_cohort_label=prospective_cohort_label,
            **metrics,
        )
