"""Comparador observacional multi-pregão da qualidade do Delta real."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class ProfitDeltaMultiSessionReport:
    status: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    sessions: int = 0
    samples: int = 0
    weighted_valid_rate: float = 0.0
    weighted_degraded_rate: float = 0.0
    weighted_low_activity_rate: float = 0.0
    weighted_dominance: float = 0.0
    weighted_persistence: float = 0.0
    weighted_zero_delta_rate: float = 0.0
    weighted_duplicate_rate: float = 0.0
    weighted_aggression_availability_rate: float = 0.0
    valid_rate_spread: float = 0.0
    duplicate_rate_spread: float = 0.0
    degraded_sessions: int = 0
    unstable_sessions: int = 0
    strong_sessions: int = 0
    promising_sessions: int = 0
    weak_sessions: int = 0
    total_anomalies: int = 0
    max_abs_delta: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ProfitDeltaMultiSessionComparator:
    """Mede estabilidade da fonte e qualidade do Delta entre pregões."""

    VERSION = "RC1-REAL-DELTA-MULTI-SESSION"
    MIN_SESSIONS = 3
    MIN_SAMPLES = 300
    MAX_WEIGHTED_DEGRADED_RATE = 0.20
    MAX_WEIGHTED_DUPLICATE_RATE = 0.50
    MIN_WEIGHTED_AGGRESSION_AVAILABILITY = 0.80
    MAX_VALID_RATE_SPREAD = 0.25
    MAX_DUPLICATE_RATE_SPREAD = 0.30
    STRONG_VALID_RATE = 0.80
    PROMISING_VALID_RATE = 0.60

    def compare(self, reports) -> ProfitDeltaMultiSessionReport:
        reports = tuple(report for report in reports if int(getattr(report, "samples", 0) or 0) > 0)
        sessions = len(reports)
        samples = sum(int(getattr(report, "samples", 0) or 0) for report in reports)

        if sessions == 0:
            return ProfitDeltaMultiSessionReport()

        weighted_valid = self._weighted(reports, "valid_rate", samples)
        weighted_degraded = self._weighted(reports, "degraded_rate", samples)
        weighted_low_activity = self._weighted(reports, "low_activity_rate", samples)
        weighted_dominance = self._weighted(reports, "average_dominance", samples)
        weighted_persistence = self._weighted(reports, "average_persistence", samples)
        weighted_zero = self._weighted(reports, "average_zero_delta_rate", samples)
        weighted_duplicate = self._weighted(reports, "average_duplicate_rate", samples)
        weighted_aggression = self._weighted(reports, "aggression_availability_rate", samples)

        valid_values = [float(getattr(report, "valid_rate", 0.0) or 0.0) for report in reports]
        duplicate_values = [float(getattr(report, "average_duplicate_rate", 0.0) or 0.0) for report in reports]
        valid_spread = max(valid_values) - min(valid_values) if valid_values else 0.0
        duplicate_spread = max(duplicate_values) - min(duplicate_values) if duplicate_values else 0.0

        statuses = [str(getattr(report, "status", "") or "") for report in reports]
        degraded_sessions = sum(status == "DEGRADED_SESSION" for status in statuses)
        unstable_sessions = sum(status == "UNSTABLE_SOURCE" for status in statuses)
        strong_sessions = sum(status == "STRONG_VALID_SESSION" for status in statuses)
        promising_sessions = sum(status == "PROMISING_VALID_SESSION" for status in statuses)
        weak_sessions = sum(status == "WEAK_VALID_SESSION" for status in statuses)

        if sessions < self.MIN_SESSIONS or samples < self.MIN_SAMPLES:
            status = "INSUFFICIENT_DATA"
            recommendation = "COLLECT_MORE_DATA"
        elif degraded_sessions > 0 or unstable_sessions > 0:
            status = "SOURCE_REVIEW_REQUIRED"
            recommendation = "REVIEW_SOURCE"
        elif (
            weighted_degraded >= self.MAX_WEIGHTED_DEGRADED_RATE
            or weighted_duplicate >= self.MAX_WEIGHTED_DUPLICATE_RATE
            or weighted_aggression < self.MIN_WEIGHTED_AGGRESSION_AVAILABILITY
        ):
            status = "DEGRADED_MULTI_SESSION"
            recommendation = "REVIEW_SOURCE"
        elif valid_spread > self.MAX_VALID_RATE_SPREAD or duplicate_spread > self.MAX_DUPLICATE_RATE_SPREAD:
            status = "INCONSISTENT"
            recommendation = "KEEP_OBSERVING"
        elif weighted_valid >= self.STRONG_VALID_RATE:
            status = "STABLE_STRONG"
            recommendation = "KEEP_OBSERVING"
        elif weighted_valid >= self.PROMISING_VALID_RATE:
            status = "STABLE_PROMISING"
            recommendation = "KEEP_OBSERVING"
        else:
            status = "STABLE_WEAK"
            recommendation = "KEEP_OBSERVING"

        return ProfitDeltaMultiSessionReport(
            status=status,
            recommendation=recommendation,
            sessions=sessions,
            samples=samples,
            weighted_valid_rate=round(weighted_valid, 4),
            weighted_degraded_rate=round(weighted_degraded, 4),
            weighted_low_activity_rate=round(weighted_low_activity, 4),
            weighted_dominance=round(weighted_dominance, 4),
            weighted_persistence=round(weighted_persistence, 4),
            weighted_zero_delta_rate=round(weighted_zero, 4),
            weighted_duplicate_rate=round(weighted_duplicate, 4),
            weighted_aggression_availability_rate=round(weighted_aggression, 4),
            valid_rate_spread=round(valid_spread, 4),
            duplicate_rate_spread=round(duplicate_spread, 4),
            degraded_sessions=degraded_sessions,
            unstable_sessions=unstable_sessions,
            strong_sessions=strong_sessions,
            promising_sessions=promising_sessions,
            weak_sessions=weak_sessions,
            total_anomalies=sum(int(getattr(report, "total_anomalies", 0) or 0) for report in reports),
            max_abs_delta=max((float(getattr(report, "max_abs_delta", 0.0) or 0.0) for report in reports), default=0.0),
            passive_only=True,
        )

    @staticmethod
    def _weighted(reports, field: str, total_samples: int) -> float:
        if total_samples <= 0:
            return 0.0
        return sum(
            float(getattr(report, field, 0.0) or 0.0)
            * int(getattr(report, "samples", 0) or 0)
            for report in reports
        ) / total_samples
