"""Comparação observacional da qualidade do calendário entre pregões RC7."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EconomicCalendarMultiSessionReport:
    classification: str
    session_count: int
    total_samples: int
    average_availability: float
    average_stale_rate: float
    action: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    observational_only: bool = True


class EconomicCalendarMultiSessionComparator:
    NAME = "EconomicCalendarMultiSessionComparator"
    VERSION = "RC7"

    def __init__(self, min_sessions=3, min_total_samples=60, min_availability=0.95, max_stale_rate=0.10):
        self.min_sessions = int(min_sessions)
        self.min_total_samples = int(min_total_samples)
        self.min_availability = float(min_availability)
        self.max_stale_rate = float(max_stale_rate)
        if self.min_sessions <= 0 or self.min_total_samples <= 0:
            raise ValueError("Mínimos de sessões/amostras devem ser positivos.")
        if not 0.0 <= self.min_availability <= 1.0:
            raise ValueError("min_availability deve estar entre 0 e 1.")
        if not 0.0 <= self.max_stale_rate <= 1.0:
            raise ValueError("max_stale_rate deve estar entre 0 e 1.")

    def compare(self, records) -> EconomicCalendarMultiSessionReport:
        records = tuple(records)
        if not records:
            return self._report("NO_DATA", 0, 0, 0.0, 0.0, "OBSERVE", ("NO_SESSIONS",))

        summaries = [record.get("summary", {}) for record in records]
        reports = [record.get("report", {}) for record in records]
        count = len(records)
        total_samples = sum(int(item.get("sample_count", 0) or 0) for item in summaries)
        avg_availability = sum(float(item.get("availability_rate", 0.0) or 0.0) for item in summaries) / count
        avg_stale = sum(float(item.get("stale_rate", 0.0) or 0.0) for item in summaries) / count

        if count < self.min_sessions or total_samples < self.min_total_samples:
            return self._report(
                "INSUFFICIENT_SESSIONS", count, total_samples, avg_availability, avg_stale,
                "OBSERVE", ("MULTI_SESSION_MINIMUM_NOT_REACHED",),
            )

        degraded = sum(item.get("classification") == "DEGRADED_SESSION" for item in reports)
        reasons = []
        if degraded:
            reasons.append("DEGRADED_SESSION_PRESENT")
        if avg_availability < self.min_availability:
            reasons.append("LOW_AVERAGE_AVAILABILITY")
        if avg_stale > self.max_stale_rate:
            reasons.append("HIGH_AVERAGE_STALE_RATE")
        if reasons:
            classification = "DEGRADED_MULTI_SESSION" if degraded == count else "INCONSISTENT_SOURCE"
            return self._report(
                classification, count, total_samples, avg_availability, avg_stale,
                "REVIEW_SOURCE", tuple(reasons),
            )
        return self._report(
            "STABLE_VALID_SOURCE", count, total_samples, avg_availability, avg_stale,
            "OBSERVE", ("MULTI_SESSION_QUALITY_ACCEPTABLE",),
        )

    @staticmethod
    def _report(classification, count, samples, availability, stale, action, reasons):
        return EconomicCalendarMultiSessionReport(
            classification=classification,
            session_count=count,
            total_samples=samples,
            average_availability=availability,
            average_stale_rate=stale,
            action=action,
            reasons=reasons,
        )
