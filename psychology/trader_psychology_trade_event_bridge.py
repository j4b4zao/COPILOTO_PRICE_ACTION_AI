"""Ponte controlada de eventos de trade para Psicologia (RC9)."""

from __future__ import annotations

from collections.abc import Mapping

from core.event_types import EventType
from psychology.trader_psychology_session_provider import (
    TraderPsychologySessionProvider,
)


class TraderPsychologyTradeEventBridge:
    """Consome fatos de trade sem participar da execução operacional."""

    NAME = "TraderPsychologyTradeEventBridge"
    VERSION = "RC9"

    def __init__(self, *, event_bus, session_provider):
        if event_bus is None:
            raise TypeError("event_bus é obrigatório.")
        for method in ("subscribe", "unsubscribe"):
            if not callable(getattr(event_bus, method, None)):
                raise TypeError(
                    f"event_bus deve expor {method}()."
                )
        if not isinstance(
            session_provider,
            TraderPsychologySessionProvider,
        ):
            raise TypeError(
                "session_provider deve ser "
                "TraderPsychologySessionProvider."
            )

        self.event_bus = event_bus
        self.session_provider = session_provider
        self.connected = False
        self.accepted_events = 0
        self.rejected_events = 0
        self.last_error = None

    def connect(self):
        if self.connected:
            return self
        self.event_bus.subscribe(
            EventType.TRADE_OPENED,
            self._on_trade_opened,
        )
        self.event_bus.subscribe(
            EventType.TRADE_CLOSED,
            self._on_trade_closed,
        )
        self.connected = True
        return self

    def disconnect(self):
        if not self.connected:
            return self
        self.event_bus.unsubscribe(
            EventType.TRADE_OPENED,
            self._on_trade_opened,
        )
        self.event_bus.unsubscribe(
            EventType.TRADE_CLOSED,
            self._on_trade_closed,
        )
        self.connected = False
        return self

    def _on_trade_opened(self, event):
        try:
            data = self._event_data(
                event,
                EventType.TRADE_OPENED,
            )
            self.session_provider.record_trade_open(
                quantity=data["quantity"],
                plan_checklist_passed=data[
                    "plan_checklist_passed"
                ],
                chased_price=data.get("chased_price", False),
                skipped_confirmation=data.get(
                    "skipped_confirmation",
                    False,
                ),
            )
        except Exception as exc:
            self._reject(exc)
            return
        self._accept()

    def _on_trade_closed(self, event):
        try:
            data = self._event_data(
                event,
                EventType.TRADE_CLOSED,
            )
            self.session_provider.record_trade_close(
                result_r=data["result_r"],
            )
        except Exception as exc:
            self._reject(exc)
            return
        self._accept()

    @staticmethod
    def _event_data(event, expected_type):
        if event is None:
            raise TypeError("event é obrigatório.")
        if getattr(event, "type", None) != expected_type:
            raise ValueError("Tipo de evento incompatível.")
        data = getattr(event, "data", None)
        if not isinstance(data, Mapping):
            raise TypeError("event.data deve ser um mapping.")
        return data

    def _accept(self):
        self.accepted_events += 1
        self.last_error = None

    def _reject(self, exc):
        self.rejected_events += 1
        self.last_error = f"{type(exc).__name__}: {exc}"
