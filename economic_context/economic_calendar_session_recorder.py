"""Recorder observacional de qualidade do calendário econômico RC6."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime

from economic_context.economic_calendar_state import EconomicCalendarState


@dataclass(frozen=True, slots=True)
class EconomicCalendarSessionSample:
    observed_at: datetime
    status: str
    source: str
    provider_valid: bool
    stale: bool
    high_impact_window: bool
    rejected_count: int
    duplicate_count: int


class EconomicCalendarSessionRecorder:
    NAME = "EconomicCalendarSessionRecorder"
    VERSION = "RC6"

    def __init__(self, max_samples=5000):
        max_samples = int(max_samples)
        if max_samples <= 0:
            raise ValueError("max_samples deve ser positivo.")
        self._samples = deque(maxlen=max_samples)

    def record(self, state: EconomicCalendarState, diagnostics: dict):
        if not isinstance(state, EconomicCalendarState):
            raise TypeError("Recorder requer EconomicCalendarState.")
        provider = diagnostics.get("provider", {})
        normalization = diagnostics.get("normalization", {})
        sample = EconomicCalendarSessionSample(
            observed_at=state.observed_at,
            status=state.status,
            source=state.source or str(provider.get("source", "")),
            provider_valid=bool(provider.get("valid", False)),
            stale=bool(state.stale or provider.get("stale", False)),
            high_impact_window=state.has_high_impact_window,
            rejected_count=int(normalization.get("rejected_count", 0) or 0),
            duplicate_count=int(normalization.get("duplicate_count", 0) or 0),
        )
        self._samples.append(sample)
        return sample

    @property
    def samples(self):
        return tuple(self._samples)

    def summary(self) -> dict:
        samples = self.samples
        total = len(samples)
        statuses = Counter(sample.status for sample in samples)
        sources = Counter(sample.source for sample in samples if sample.source)
        if total == 0:
            return {
                "sample_count": 0,
                "availability_rate": 0.0,
                "stale_rate": 0.0,
                "high_impact_window_rate": 0.0,
                "rejected_row_count": 0,
                "duplicate_row_count": 0,
                "statuses": {},
                "sources": {},
            }
        return {
            "sample_count": total,
            "availability_rate": sum(sample.provider_valid for sample in samples) / total,
            "stale_rate": sum(sample.stale for sample in samples) / total,
            "high_impact_window_rate": sum(sample.high_impact_window for sample in samples) / total,
            "rejected_row_count": sum(sample.rejected_count for sample in samples),
            "duplicate_row_count": sum(sample.duplicate_count for sample in samples),
            "statuses": dict(statuses),
            "sources": dict(sources),
        }

    def clear(self):
        self._samples.clear()
