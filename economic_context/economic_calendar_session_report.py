"""Classificação observacional da qualidade de uma sessão econômica RC6."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EconomicCalendarSessionReport:
    classification: str
    sample_count: int
    availability_rate: float
    stale_rate: float
    action: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    observational_only: bool = True


class EconomicCalendarSessionAnalyzer:
    NAME = "EconomicCalendarSessionAnalyzer"
    VERSION = "RC6"

    def __init__(self, min_samples=20, min_availability=0.95, max_stale_rate=0.10):
        self.min_samples = int(min_samples)
        self.min_availability = float(min_availability)
        self.max_stale_rate = float(max_stale_rate)
        if self.min_samples <= 0:
            raise ValueError("min_samples deve ser positivo.")
        if not 0.0 <= self.min_availability <= 1.0:
            raise ValueError("min_availability deve estar entre 0 e 1.")
        if not 0.0 <= self.max_stale_rate <= 1.0:
            raise ValueError("max_stale_rate deve estar entre 0 e 1.")

    def analyze(self, summary: dict) -> EconomicCalendarSessionReport:
        count = int(summary.get("sample_count", 0) or 0)
        availability = float(summary.get("availability_rate", 0.0) or 0.0)
        stale = float(summary.get("stale_rate", 0.0) or 0.0)
        rejected = int(summary.get("rejected_row_count", 0) or 0)

        if count == 0:
            classification, action, reasons = "NO_DATA", "OBSERVE", ("NO_SESSION_SAMPLES",)
        elif count < self.min_samples:
            classification, action, reasons = "INSUFFICIENT_DATA", "OBSERVE", ("MINIMUM_SAMPLES_NOT_REACHED",)
        else:
            reasons_list = []
            if availability < self.min_availability:
                reasons_list.append("LOW_PROVIDER_AVAILABILITY")
            if stale > self.max_stale_rate:
                reasons_list.append("EXCESSIVE_STALE_CACHE")
            if rejected > 0:
                reasons_list.append("PAYLOAD_ROWS_REJECTED")
            if reasons_list:
                classification, action, reasons = "DEGRADED_SESSION", "REVIEW_SOURCE", tuple(reasons_list)
            else:
                classification, action, reasons = "VALID_SESSION", "OBSERVE", ("SOURCE_QUALITY_ACCEPTABLE",)

        return EconomicCalendarSessionReport(
            classification=classification,
            sample_count=count,
            availability_rate=availability,
            stale_rate=stale,
            action=action,
            reasons=reasons,
        )
