"""Resultado normalizado de aquisição do calendário econômico RC3."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from economic_context.economic_event import EconomicEvent


@dataclass(frozen=True, slots=True)
class EconomicCalendarProviderResult:
    available: bool
    valid: bool
    events: tuple[EconomicEvent, ...] = field(default_factory=tuple)
    source: str = ""
    fetched_at: datetime | None = None
    expires_at: datetime | None = None
    stale: bool = False
    error: str = ""

    def __post_init__(self) -> None:
        events = tuple(self.events)
        if not all(isinstance(event, EconomicEvent) for event in events):
            raise TypeError("ProviderResult requer somente EconomicEvent.")
        for value, name in ((self.fetched_at, "fetched_at"), (self.expires_at, "expires_at")):
            if value is not None and (not isinstance(value, datetime) or value.tzinfo is None):
                raise ValueError(f"{name} deve ser datetime com fuso horário.")
        if self.valid and not self.available:
            raise ValueError("Resultado válido precisa estar disponível.")
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "source", str(self.source).strip().upper())
        object.__setattr__(self, "error", str(self.error).strip())

    @classmethod
    def unavailable(cls, *, source="", error="") -> "EconomicCalendarProviderResult":
        return cls(available=False, valid=False, source=source, error=error)
