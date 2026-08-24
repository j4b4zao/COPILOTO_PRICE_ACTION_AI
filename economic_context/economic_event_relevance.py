"""Relevância conservadora de eventos para WIN e WDO RC2."""

from __future__ import annotations

from economic_context.economic_event import EconomicEvent


class EconomicEventRelevance:
    NAME = "EconomicEventRelevance"
    VERSION = "RC2"

    RELEVANT_CURRENCIES = {
        "WIN": frozenset({"BRL", "USD"}),
        "WDO": frozenset({"BRL", "USD"}),
    }
    RELEVANT_COUNTRIES = {
        "WIN": frozenset({"BR", "BRAZIL", "BRASIL", "US", "USA"}),
        "WDO": frozenset({"BR", "BRAZIL", "BRASIL", "US", "USA"}),
    }

    def filter(self, events, *, symbol: str) -> tuple[EconomicEvent, ...]:
        family = self.instrument_family(symbol)
        if family not in self.RELEVANT_CURRENCIES:
            return ()
        return tuple(
            event for event in events
            if self.is_relevant(event, family=family)
        )

    def is_relevant(self, event: EconomicEvent, *, family: str) -> bool:
        if not isinstance(event, EconomicEvent):
            raise TypeError("Relevância requer EconomicEvent.")
        return (
            event.currency in self.RELEVANT_CURRENCIES[family]
            or event.country in self.RELEVANT_COUNTRIES[family]
        )

    @staticmethod
    def instrument_family(symbol: str) -> str:
        normalized = str(symbol).strip().upper()
        if normalized.startswith("WIN"):
            return "WIN"
        if normalized.startswith("WDO"):
            return "WDO"
        return ""
