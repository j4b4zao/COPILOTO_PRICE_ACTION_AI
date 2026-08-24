"""Provider RC3 com cache, expiração e fallback observacional seguro."""

from __future__ import annotations

from datetime import datetime, timedelta

from economic_context.economic_calendar_provider_result import EconomicCalendarProviderResult


class FailSafeEconomicCalendarProvider:
    NAME = "FailSafeEconomicCalendarProvider"
    VERSION = "RC3"

    def __init__(self, fetcher, *, source="EXTERNAL", ttl_minutes=15, max_stale_minutes=60):
        if not callable(fetcher):
            raise TypeError("FailSafeEconomicCalendarProvider requer fetcher callable.")
        self.fetcher = fetcher
        self.source = str(source).strip().upper() or "EXTERNAL"
        self.ttl = timedelta(minutes=self._positive(ttl_minutes, "ttl_minutes"))
        self.max_stale = timedelta(minutes=self._positive(max_stale_minutes, "max_stale_minutes"))
        if self.max_stale < self.ttl:
            raise ValueError("max_stale_minutes não pode ser menor que ttl_minutes.")
        self.last_result = EconomicCalendarProviderResult.unavailable(source=self.source)
        self._cache = None

    def get_events(self, *, now: datetime):
        return self.get_result(now=now).events

    def get_result(self, *, now: datetime) -> EconomicCalendarProviderResult:
        self._validate_now(now)
        if self._cache is not None and self._cache.expires_at > now:
            self.last_result = self._cache
            return self.last_result

        try:
            events = tuple(self.fetcher(now=now))
            expires_at = now + self.ttl
            self._cache = EconomicCalendarProviderResult(
                available=True,
                valid=True,
                events=events,
                source=self.source,
                fetched_at=now,
                expires_at=expires_at,
            )
            self.last_result = self._cache
            return self.last_result
        except Exception as exc:  # provider externo nunca derruba o núcleo
            self.last_result = self._fallback(now=now, error=str(exc))
            return self.last_result

    def _fallback(self, *, now, error):
        if self._cache is not None and self._cache.fetched_at is not None:
            age = now - self._cache.fetched_at
            if timedelta(0) <= age <= self.max_stale:
                return EconomicCalendarProviderResult(
                    available=True,
                    valid=True,
                    events=self._cache.events,
                    source=self.source,
                    fetched_at=self._cache.fetched_at,
                    expires_at=self._cache.expires_at,
                    stale=True,
                    error=error,
                )
        return EconomicCalendarProviderResult.unavailable(source=self.source, error=error)

    @staticmethod
    def _validate_now(now):
        if not isinstance(now, datetime):
            raise TypeError("Provider requer now datetime.")
        if now.tzinfo is None:
            raise ValueError("Provider requer now com fuso horário.")

    @staticmethod
    def _positive(value, name):
        converted = float(value)
        if converted <= 0:
            raise ValueError(f"{name} deve ser positivo.")
        return converted
