"""Normalização provider-agnostic de calendários econômicos RC4."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from economic_context.economic_calendar_normalization_result import (
    EconomicCalendarNormalizationResult,
)
from economic_context.economic_event import EconomicEvent


class EconomicCalendarPayloadNormalizer:
    NAME = "EconomicCalendarPayloadNormalizer"
    VERSION = "RC4"

    TITLE_KEYS = ("title", "name", "event", "evento")
    DATETIME_KEYS = ("scheduled_at", "datetime", "date_time", "timestamp", "date", "data")
    IMPACT_KEYS = ("impact", "importance", "priority", "impacto")
    CURRENCY_KEYS = ("currency", "moeda")
    COUNTRY_KEYS = ("country", "country_code", "pais", "país")

    IMPACT_MAP = {
        "1": "LOW", "LOW": "LOW", "BAIXO": "LOW",
        "2": "MEDIUM", "MEDIUM": "MEDIUM", "MEDIO": "MEDIUM", "MÉDIO": "MEDIUM",
        "3": "HIGH", "HIGH": "HIGH", "ALTO": "HIGH",
    }

    def normalize(self, payloads, *, source="EXTERNAL", default_timezone="UTC"):
        zone = self._zone(default_timezone)
        try:
            rows = tuple(payloads)
        except TypeError as exc:
            raise TypeError("Payload econômico deve ser iterável.") from exc

        selected = {}
        errors = []
        duplicates = 0

        for index, row in enumerate(rows):
            try:
                event = self._normalize_row(row, source=source, zone=zone)
            except (TypeError, ValueError) as exc:
                errors.append(f"ROW_{index}:{exc}")
                continue

            key = self._dedupe_key(event)
            current = selected.get(key)
            if current is None:
                selected[key] = event
                continue
            duplicates += 1
            if event.impact_level > current.impact_level:
                selected[key] = event

        events = tuple(sorted(selected.values(), key=lambda item: item.scheduled_at))
        return EconomicCalendarNormalizationResult(
            events=events,
            received_count=len(rows),
            rejected_count=len(errors),
            duplicate_count=duplicates,
            errors=tuple(errors),
        )

    def _normalize_row(self, row, *, source, zone):
        if not isinstance(row, dict):
            raise TypeError("linha deve ser dict")
        title = self._required(row, self.TITLE_KEYS, "title")
        scheduled_at = self._datetime(self._required(row, self.DATETIME_KEYS, "scheduled_at"), zone)
        impact = self._impact(self._required(row, self.IMPACT_KEYS, "impact"))
        currency = self._optional(row, self.CURRENCY_KEYS)
        country = self._optional(row, self.COUNTRY_KEYS)
        return EconomicEvent(
            title=title,
            scheduled_at=scheduled_at,
            impact=impact,
            currency=currency,
            country=country,
            source=source,
        )

    @staticmethod
    def _required(row, keys, label):
        value = EconomicCalendarPayloadNormalizer._optional(row, keys)
        if value is None or str(value).strip() == "":
            raise ValueError(f"{label} ausente")
        return value

    @staticmethod
    def _optional(row, keys):
        for key in keys:
            if key in row and row[key] is not None:
                return row[key]
        return ""

    @classmethod
    def _impact(cls, value):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("impact inválido")
        key = str(value).strip().upper()
        try:
            return cls.IMPACT_MAP[key]
        except KeyError as exc:
            raise ValueError(f"impact desconhecido: {value!r}") from exc

    @staticmethod
    def _datetime(value, zone):
        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value).strip()
            if not text:
                raise ValueError("scheduled_at vazio")
            if text.endswith(("Z", "z")):
                text = text[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError as exc:
                raise ValueError(f"scheduled_at inválido: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=zone)
        return parsed

    @staticmethod
    def _zone(value):
        if hasattr(value, "utcoffset"):
            return value
        try:
            return ZoneInfo(str(value))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"fuso horário inválido: {value!r}") from exc

    @staticmethod
    def _dedupe_key(event):
        title = " ".join(event.title.casefold().split())
        instant = event.scheduled_at.astimezone(timezone.utc).isoformat()
        return title, instant, event.currency
