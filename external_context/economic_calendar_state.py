"""Estado informativo do calendário econômico RC5.0."""

from dataclasses import dataclass, field
from datetime import datetime

from external_context.economic_event import EconomicEvent


@dataclass(slots=True)
class EconomicCalendarState:

    valid: bool = False
    timestamp: datetime | None = None
    timezone: str = "America/Sao_Paulo"
    events: list[EconomicEvent] = field(default_factory=list)

    next_event: EconomicEvent | None = None
    minutes_to_event: float | None = None
    in_event_window: bool = False
    event_risk: str = "NONE"

    window_before_minutes: int = 30
    window_after_minutes: int = 15

    reasons: list[str] = field(default_factory=list)

    def update(
        self,
        events,
        now,
    ):
        if not isinstance(now, datetime):
            raise TypeError(
                "Horário de referência deve ser datetime."
            )

        normalized = list(events or ())

        if not all(
            isinstance(event, EconomicEvent)
            for event in normalized
        ):
            raise TypeError(
                "Calendário aceita somente EconomicEvent."
            )

        self.timestamp = now
        self.events = sorted(
            normalized,
            key=lambda event: event.scheduled_at,
        )
        self.valid = True
        self._classify(now)
        return self

    def _classify(self, now):
        self.next_event = None
        self.minutes_to_event = None
        self.in_event_window = False
        self.event_risk = "NONE"
        self.reasons.clear()

        active = []

        for event in self.events:
            minutes = (
                event.scheduled_at - now
            ).total_seconds() / 60.0

            if (
                -self.window_after_minutes
                <= minutes
                <= self.window_before_minutes
            ):
                active.append((event, minutes))

        candidates = active or [
            (
                event,
                (
                    event.scheduled_at - now
                ).total_seconds() / 60.0,
            )
            for event in self.events
            if event.scheduled_at >= now
        ]

        if not candidates:
            self.reasons.append(
                "Nenhum evento econômico futuro disponível."
            )
            return

        event, minutes = min(
            candidates,
            key=lambda item: (
                abs(item[1]) if active else item[1],
                item[0].scheduled_at,
            ),
        )

        self.next_event = event
        self.minutes_to_event = round(minutes, 2)
        self.in_event_window = bool(active)
        self.event_risk = (
            event.impact
            if self.in_event_window
            else "NONE"
        )

        if self.in_event_window:
            self.reasons.append(
                f"Evento {event.impact}: {event.title}."
            )
            self.reasons.append(
                "Janela informativa de evento ativa."
            )
        else:
            self.reasons.append(
                f"Próximo evento: {event.title}."
            )

    def clear(self):
        self.valid = False
        self.timestamp = None
        self.events.clear()
        self.next_event = None
        self.minutes_to_event = None
        self.in_event_window = False
        self.event_risk = "NONE"
        self.reasons.clear()
