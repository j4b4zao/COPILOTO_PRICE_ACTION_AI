"""Classificação observacional de proximidade de eventos econômicos.

RC1 não consulta rede e não modifica Strategy, Score, Risk ou Decision. Recebe
eventos já normalizados para permitir testes controlados e futura conexão com um
provider real.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from economic_context.economic_calendar_state import EconomicCalendarState
from economic_context.economic_event import EconomicEvent


class EconomicCalendarEngine:
    NAME = "EconomicCalendarEngine"
    VERSION = "RC1"

    def __init__(self, high_window_minutes: int = 15, medium_window_minutes: int = 10):
        self.high_window_minutes = self._positive_int(high_window_minutes, "high_window_minutes")
        self.medium_window_minutes = self._positive_int(medium_window_minutes, "medium_window_minutes")

    def evaluate(
        self,
        events: Iterable[EconomicEvent],
        *,
        now: datetime,
    ) -> EconomicCalendarState:
        if not isinstance(now, datetime):
            raise TypeError("EconomicCalendarEngine requer now datetime.")
        if now.tzinfo is None:
            raise ValueError("EconomicCalendarEngine requer now com fuso horário.")

        normalized = tuple(sorted(tuple(events), key=lambda event: event.scheduled_at))
        if not all(isinstance(event, EconomicEvent) for event in normalized):
            raise TypeError("Todos os itens devem ser EconomicEvent.")

        active = tuple(event for event in normalized if self._is_active(event, now))
        upcoming = tuple(event for event in normalized if event.scheduled_at >= now)
        next_event = upcoming[0] if upcoming else None
        minutes_to_next = (
            round((next_event.scheduled_at - now).total_seconds() / 60.0, 2)
            if next_event else None
        )

        if any(event.impact == "HIGH" for event in active):
            status = "HIGH_IMPACT_WINDOW"
            reasons = ("HIGH_IMPACT_EVENT_NEAR",)
        elif any(event.impact == "MEDIUM" for event in active):
            status = "CAUTION"
            reasons = ("MEDIUM_IMPACT_EVENT_NEAR",)
        elif not normalized:
            status = "NO_EVENTS"
            reasons = ("CALENDAR_EMPTY",)
        else:
            status = "CLEAR"
            reasons = ("NO_RELEVANT_EVENT_IN_WINDOW",)

        return EconomicCalendarState(
            status=status,
            observed_at=now,
            events=normalized,
            active_events=active,
            next_event=next_event,
            minutes_to_next=minutes_to_next,
            reasons=reasons,
        )

    def _is_active(self, event: EconomicEvent, now: datetime) -> bool:
        minutes = abs((event.scheduled_at - now).total_seconds()) / 60.0
        if event.impact == "HIGH":
            return minutes <= self.high_window_minutes
        if event.impact == "MEDIUM":
            return minutes <= self.medium_window_minutes
        return False

    @staticmethod
    def _positive_int(value: int, name: str) -> int:
        normalized = int(value)
        if normalized <= 0:
            raise ValueError(f"{name} deve ser positivo.")
        return normalized
