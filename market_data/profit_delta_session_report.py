"""Relatório final observacional de uma sessão de Delta real."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ProfitDeltaSessionReport:
    status: str = "NO_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    samples: int = 0
    valid_rate: float = 0.0
    degraded_rate: float = 0.0
    low_activity_rate: float = 0.0
    average_dominance: float = 0.0
    average_persistence: float = 0.0
    average_zero_delta_rate: float = 0.0
    average_duplicate_rate: float = 0.0
    aggression_availability_rate: float = 0.0
    total_anomalies: int = 0
    max_abs_delta: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ProfitDeltaSessionReportBuilder:
    """Classifica a qualidade consolidada do pregão sem efeito operacional."""

    VERSION = "RC1-REAL-DELTA-SESSION-REPORT"
    MIN_SAMPLES = 100
    STRONG_VALID_RATE = 0.80
    PROMISING_VALID_RATE = 0.60
    MAX_DEGRADED_RATE = 0.20
    MAX_DUPLICATE_RATE = 0.50
    MIN_AGGRESSION_AVAILABILITY = 0.80

    def build(self, recorder) -> ProfitDeltaSessionReport:
        summary = recorder.summary()
        samples = int(summary.get("samples", 0) or 0)
        if samples == 0:
            return ProfitDeltaSessionReport()

        valid_rate = float(summary.get("valid_rate", 0.0) or 0.0)
        degraded_rate = float(summary.get("degraded_rate", 0.0) or 0.0)
        duplicate_rate = float(summary.get("average_duplicate_rate", 0.0) or 0.0)
        aggression_rate = float(summary.get("average_aggression_availability_rate", 0.0) or 0.0)
        anomalies = int(summary.get("total_anomalies", 0) or 0)

        if samples < self.MIN_SAMPLES:
            status = "INSUFFICIENT_DATA"
            recommendation = "COLLECT_MORE_DATA"
        elif degraded_rate >= self.MAX_DEGRADED_RATE or aggression_rate < self.MIN_AGGRESSION_AVAILABILITY:
            status = "DEGRADED_SESSION"
            recommendation = "REVIEW_SOURCE"
        elif duplicate_rate >= self.MAX_DUPLICATE_RATE:
            status = "UNSTABLE_SOURCE"
            recommendation = "REVIEW_SOURCE"
        elif valid_rate >= self.STRONG_VALID_RATE and anomalies == 0:
            status = "STRONG_VALID_SESSION"
            recommendation = "KEEP_OBSERVING"
        elif valid_rate >= self.PROMISING_VALID_RATE:
            status = "PROMISING_VALID_SESSION"
            recommendation = "KEEP_OBSERVING"
        else:
            status = "WEAK_VALID_SESSION"
            recommendation = "KEEP_OBSERVING"

        return ProfitDeltaSessionReport(
            status=status,
            recommendation=recommendation,
            samples=samples,
            valid_rate=round(valid_rate, 4),
            degraded_rate=round(degraded_rate, 4),
            low_activity_rate=float(summary.get("low_activity_rate", 0.0) or 0.0),
            average_dominance=float(summary.get("average_dominance", 0.0) or 0.0),
            average_persistence=float(summary.get("average_persistence", 0.0) or 0.0),
            average_zero_delta_rate=float(summary.get("average_zero_delta_rate", 0.0) or 0.0),
            average_duplicate_rate=round(duplicate_rate, 4),
            aggression_availability_rate=round(aggression_rate, 4),
            total_anomalies=anomalies,
            max_abs_delta=float(summary.get("max_abs_delta", 0.0) or 0.0),
            passive_only=True,
        )
