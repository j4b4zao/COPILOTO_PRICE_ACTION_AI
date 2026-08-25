"""Contratos de aquisição do calendário econômico RC2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from economic_context.economic_event import EconomicEvent


class EconomicCalendarProvider(ABC):
    NAME = "EconomicCalendarProvider"
    VERSION = "RC2"

    @abstractmethod
    def get_events(self, *, now: datetime) -> tuple[EconomicEvent, ...]:
        """Retorna eventos normalizados sem interpretar ou gerar sinais."""
        raise NotImplementedError


class ControlledEconomicCalendarProvider(EconomicCalendarProvider):
    """Provider determinístico para testes, replay e validação offline."""

    NAME = "ControlledEconomicCalendarProvider"

    def __init__(self, events=()):
        normalized = tuple(events)
        if not all(isinstance(event, EconomicEvent) for event in normalized):
            raise TypeError("ControlledEconomicCalendarProvider requer EconomicEvent.")
        self._events = normalized

    def get_events(self, *, now: datetime) -> tuple[EconomicEvent, ...]:
        if not isinstance(now, datetime):
            raise TypeError("Provider requer now datetime.")
        return self._events
