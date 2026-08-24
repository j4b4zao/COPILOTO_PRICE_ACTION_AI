"""Provider -> relevância -> engine -> AnalysisContext, somente observacional."""

from __future__ import annotations

from datetime import datetime

from economic_context.economic_calendar_engine import EconomicCalendarEngine
from economic_context.economic_calendar_provider import EconomicCalendarProvider
from economic_context.economic_calendar_state import EconomicCalendarState
from economic_context.economic_event_relevance import EconomicEventRelevance


class EconomicCalendarService:
    NAME = "EconomicCalendarService"
    VERSION = "RC2"

    def __init__(self, provider: EconomicCalendarProvider, engine=None, relevance=None):
        if not callable(getattr(provider, "get_events", None)):
            raise TypeError("Provider deve expor get_events(now=...).")
        self.provider = provider
        self.engine = engine or EconomicCalendarEngine()
        self.relevance = relevance or EconomicEventRelevance()

    def snapshot(self, *, symbol: str, now: datetime) -> EconomicCalendarState:
        events = self.provider.get_events(now=now)
        relevant = self.relevance.filter(events, symbol=symbol)
        return self.engine.evaluate(relevant, now=now)

    def attach(self, context, *, now: datetime) -> EconomicCalendarState:
        if not hasattr(context, "market") or not hasattr(context, "economic_calendar"):
            raise TypeError("Contexto incompatível com EconomicCalendarService.")
        state = self.snapshot(symbol=context.market.symbol, now=now)
        context.economic_calendar = state
        return state
