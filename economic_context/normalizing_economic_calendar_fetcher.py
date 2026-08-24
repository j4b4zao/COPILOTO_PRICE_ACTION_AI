"""Adaptador RC5 de payload bruto para eventos normalizados."""

from __future__ import annotations

from economic_context.economic_calendar_payload_normalizer import EconomicCalendarPayloadNormalizer


class NormalizingEconomicCalendarFetcher:
    NAME = "NormalizingEconomicCalendarFetcher"
    VERSION = "RC5"

    def __init__(self, raw_fetcher, *, source="EXTERNAL", default_timezone="UTC", allow_partial=True):
        if not callable(raw_fetcher):
            raise TypeError("NormalizingFetcher requer raw_fetcher callable.")
        self.raw_fetcher = raw_fetcher
        self.source = str(source).strip().upper() or "EXTERNAL"
        self.default_timezone = default_timezone
        self.allow_partial = bool(allow_partial)
        self.normalizer = EconomicCalendarPayloadNormalizer()
        self.last_normalization = None

    def __call__(self, *, now):
        payload = self.raw_fetcher(now=now)
        result = self.normalizer.normalize(
            payload,
            source=self.source,
            default_timezone=self.default_timezone,
        )
        self.last_normalization = result

        if result.received_count > 0 and not result.usable:
            raise ValueError("Nenhum evento válido no payload recebido.")
        if result.rejected_count > 0 and not self.allow_partial:
            raise ValueError("Payload parcialmente inválido rejeitado pela política estrita.")
        return result.events

    def diagnostics(self) -> dict:
        if self.last_normalization is None:
            return {
                "status": "NOT_RUN",
                "source": self.source,
                "allow_partial": self.allow_partial,
            }
        return {
            "status": "VALID" if self.last_normalization.valid else "PARTIAL",
            "source": self.source,
            "allow_partial": self.allow_partial,
            **self.last_normalization.snapshot(),
        }
