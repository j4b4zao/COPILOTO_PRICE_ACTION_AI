"""Resultado auditável da normalização de payloads econômicos RC4."""

from __future__ import annotations

from dataclasses import dataclass, field

from economic_context.economic_event import EconomicEvent


@dataclass(frozen=True, slots=True)
class EconomicCalendarNormalizationResult:
    events: tuple[EconomicEvent, ...] = field(default_factory=tuple)
    received_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def valid(self) -> bool:
        return self.rejected_count == 0

    @property
    def usable(self) -> bool:
        return bool(self.events)

    def snapshot(self) -> dict:
        return {
            "event_count": len(self.events),
            "received_count": self.received_count,
            "rejected_count": self.rejected_count,
            "duplicate_count": self.duplicate_count,
            "valid": self.valid,
            "usable": self.usable,
            "errors": list(self.errors),
        }
