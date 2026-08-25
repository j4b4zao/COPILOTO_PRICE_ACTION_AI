"""Publicador factual de eventos de trade para Psicologia (RC10)."""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.event import Event
from core.event_types import EventType


@dataclass(frozen=True, slots=True)
class TradeEventPublicationResult:
    published: bool
    event_type: str
    error: str | None = None


class TraderPsychologyTradeEventPublisher:
    """Publica fatos explícitos sem acessar execução, score ou ordens."""

    NAME = "TraderPsychologyTradeEventPublisher"
    VERSION = "RC10"

    def __init__(self, *, event_bus):
        if event_bus is None or not callable(
            getattr(event_bus, "publish", None)
        ):
            raise TypeError("event_bus deve expor publish().")

        self.event_bus = event_bus
        self.published_events = 0
        self.rejected_events = 0
        self.last_result = None

    def publish_opened(
        self,
        *,
        quantity,
        plan_checklist_passed,
        chased_price=False,
        skipped_confirmation=False,
    ):
        try:
            quantity = self._positive_number("quantity", quantity)
            self._boolean(
                "plan_checklist_passed",
                plan_checklist_passed,
            )
            self._boolean("chased_price", chased_price)
            self._boolean(
                "skipped_confirmation",
                skipped_confirmation,
            )
            event = Event(
                EventType.TRADE_OPENED,
                {
                    "quantity": quantity,
                    "plan_checklist_passed": plan_checklist_passed,
                    "chased_price": chased_price,
                    "skipped_confirmation": skipped_confirmation,
                },
            )
        except Exception as exc:
            return self._reject(EventType.TRADE_OPENED, exc)
        return self._publish(event)

    def publish_closed(self, *, result_r):
        try:
            result_r = self._finite_number("result_r", result_r)
            event = Event(
                EventType.TRADE_CLOSED,
                {"result_r": result_r},
            )
        except Exception as exc:
            return self._reject(EventType.TRADE_CLOSED, exc)
        return self._publish(event)

    def _publish(self, event):
        try:
            self.event_bus.publish(event)
        except Exception as exc:
            return self._reject(event.type, exc)

        self.published_events += 1
        self.last_result = TradeEventPublicationResult(
            published=True,
            event_type=event.type,
        )
        return self.last_result

    def _reject(self, event_type, exc):
        self.rejected_events += 1
        self.last_result = TradeEventPublicationResult(
            published=False,
            event_type=event_type,
            error=f"{type(exc).__name__}: {exc}",
        )
        return self.last_result

    @staticmethod
    def _boolean(name, value):
        if not isinstance(value, bool):
            raise TypeError(f"{name} deve ser booleano.")

    @classmethod
    def _positive_number(cls, name, value):
        number = cls._finite_number(name, value)
        if number <= 0.0:
            raise ValueError(f"{name} deve ser maior que zero.")
        return number

    @staticmethod
    def _finite_number(name, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} deve ser numérico.")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"{name} deve ser finito.")
        return number
