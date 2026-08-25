"""Mapper offline do payload Trading Economics para o contrato canônico RC10."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class TradingEconomicsCalendarMapper:
    """Converte somente eventos Brasil/EUA sem executar qualquer chamada externa."""

    NAME = "TradingEconomicsCalendarMapper"
    VERSION = "RC10"

    COUNTRY_MAP = {
        "BRAZIL": ("BR", "BRL"),
        "BR": ("BR", "BRL"),
        "UNITED STATES": ("US", "USD"),
        "US": ("US", "USD"),
        "USA": ("US", "USD"),
    }

    def __init__(self, *, source_timezone="UTC"):
        try:
            self.source_timezone = ZoneInfo(str(source_timezone))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Fuso da fonte inválido: {source_timezone!r}") from exc
        self.last_diagnostics = {
            "status": "NOT_RUN",
            "received_count": 0,
            "mapped_count": 0,
            "filtered_count": 0,
            "rejected_count": 0,
            "errors": (),
        }

    def map(self, payloads):
        try:
            rows = tuple(payloads)
        except TypeError as exc:
            raise TypeError("Payload Trading Economics deve ser iterável.") from exc

        mapped = []
        filtered = 0
        errors = []

        for index, row in enumerate(rows):
            try:
                canonical = self._map_row(row)
            except (TypeError, ValueError) as exc:
                errors.append(f"ROW_{index}:{exc}")
                continue
            if canonical is None:
                filtered += 1
                continue
            mapped.append(canonical)

        self.last_diagnostics = {
            "status": "OK" if not errors else "PARTIAL",
            "received_count": len(rows),
            "mapped_count": len(mapped),
            "filtered_count": filtered,
            "rejected_count": len(errors),
            "errors": tuple(errors),
        }
        return mapped

    def _map_row(self, row):
        if not isinstance(row, dict):
            raise TypeError("linha deve ser dict")

        country_text = self._required(row, "Country").upper()
        country_data = self.COUNTRY_MAP.get(country_text)
        if country_data is None:
            return None
        country, fallback_currency = country_data

        title = self._required(row, "Event")
        scheduled_at = self._datetime(self._required(row, "Date"))
        importance = self._importance(self._required(row, "Importance"))
        currency = str(row.get("Currency") or fallback_currency).strip().upper()

        return {
            "title": title,
            "scheduled_at": scheduled_at.isoformat(),
            "impact": importance,
            "currency": currency,
            "country": country,
        }

    def _datetime(self, value):
        text = str(value).strip()
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError(f"Date inválida: {value!r}") from exc
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=self.source_timezone)
        return parsed

    @staticmethod
    def _importance(value):
        if isinstance(value, bool):
            raise ValueError("Importance inválida")
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Importance inválida: {value!r}") from exc
        mapping = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
        try:
            return mapping[number]
        except KeyError as exc:
            raise ValueError(f"Importance fora do intervalo: {number}") from exc

    @staticmethod
    def _required(row, key):
        if key not in row or row[key] is None or str(row[key]).strip() == "":
            raise ValueError(f"{key} ausente")
        return str(row[key]).strip()
