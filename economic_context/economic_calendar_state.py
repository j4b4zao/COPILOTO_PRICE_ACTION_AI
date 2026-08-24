"""Resultado observacional da leitura do calendário econômico RC1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from economic_context.economic_event import EconomicEvent


@dataclass(frozen=True, slots=True)
class EconomicCalendarState:
    status: str
    observed_at: datetime
    events: tuple[EconomicEvent, ...] = field(default_factory=tuple)
    active_events: tuple[EconomicEvent, ...] = field(default_factory=tuple)
    next_event: EconomicEvent | None = None
    minutes_to_next: float | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)
    observational_only: bool = True

    @classmethod
    def unavailable(cls, observed_at: datetime | None = None) -> "EconomicCalendarState":
        return cls(
            status="UNAVAILABLE",
            observed_at=observed_at or datetime.now(timezone.utc),
            reasons=("CALENDAR_NOT_LOADED",),
        )

    @property
    def has_high_impact_window(self) -> bool:
        return any(event.impact == "HIGH" for event in self.active_events)

    def snapshot(self) -> dict:
        return {
            "status": self.status,
            "observed_at": self.observed_at.isoformat(),
            "event_count": len(self.events),
            "active_event_count": len(self.active_events),
            "next_event": self.next_event.title if self.next_event else None,
            "minutes_to_next": self.minutes_to_next,
            "has_high_impact_window": self.has_high_impact_window,
            "reasons": list(self.reasons),
            "observational_only": self.observational_only,
        }
