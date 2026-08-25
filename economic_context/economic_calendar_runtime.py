"""Pipeline completo e observacional do calendário econômico RC5."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from economic_context.economic_calendar_service import EconomicCalendarService
from economic_context.fail_safe_economic_calendar_provider import FailSafeEconomicCalendarProvider
from economic_context.normalizing_economic_calendar_fetcher import NormalizingEconomicCalendarFetcher
from economic_context.economic_calendar_session_recorder import EconomicCalendarSessionRecorder
from economic_context.economic_calendar_session_report import EconomicCalendarSessionAnalyzer


class EconomicCalendarRuntime:
    NAME = "EconomicCalendarRuntime"
    VERSION = "RC5"

    def __init__(
        self,
        raw_fetcher,
        *,
        source="EXTERNAL",
        default_timezone="UTC",
        allow_partial=True,
        ttl_minutes=15,
        max_stale_minutes=60,
        recorder=None,
    ):
        self.fetcher = NormalizingEconomicCalendarFetcher(
            raw_fetcher,
            source=source,
            default_timezone=default_timezone,
            allow_partial=allow_partial,
        )
        self.provider = FailSafeEconomicCalendarProvider(
            self.fetcher,
            source=source,
            ttl_minutes=ttl_minutes,
            max_stale_minutes=max_stale_minutes,
        )
        self.service = EconomicCalendarService(self.provider)
        self.recorder = recorder or EconomicCalendarSessionRecorder()
        self.session_analyzer = EconomicCalendarSessionAnalyzer()

    def snapshot(self, *, symbol: str, now: datetime):
        state = self.service.snapshot(symbol=symbol, now=now)
        normalization = self.fetcher.last_normalization
        if normalization is not None and normalization.rejected_count > 0:
            marker = (
                "PAYLOAD_PARTIALLY_REJECTED"
                if normalization.usable
                else "PAYLOAD_REJECTED"
            )
            if marker not in state.reasons:
                state = replace(state, reasons=state.reasons + (marker,))
        self.recorder.record(state, self._runtime_diagnostics())
        return state

    def attach(self, context, *, now: datetime):
        if not hasattr(context, "market") or not hasattr(context, "economic_calendar"):
            raise TypeError("Contexto incompatível com EconomicCalendarRuntime.")
        state = self.snapshot(symbol=context.market.symbol, now=now)
        context.economic_calendar = state
        return state

    def diagnostics(self) -> dict:
        diagnostics = self._runtime_diagnostics()
        summary = self.recorder.summary()
        report = self.session_analyzer.analyze(summary)
        diagnostics["session"] = summary
        diagnostics["session_report"] = {
            "classification": report.classification,
            "action": report.action,
            "reasons": list(report.reasons),
            "observational_only": report.observational_only,
        }
        return diagnostics

    def _runtime_diagnostics(self) -> dict:
        provider = self.provider.last_result
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "provider": {
                "available": provider.available,
                "valid": provider.valid,
                "source": provider.source,
                "stale": provider.stale,
                "error": provider.error,
                "event_count": len(provider.events),
            },
            "normalization": self.fetcher.diagnostics(),
            "observational_only": True,
        }
