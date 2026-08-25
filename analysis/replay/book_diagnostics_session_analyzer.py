"""
analysis/replay/book_diagnostics_session_analyzer.py

BookDiagnostics RC13 - Session Segmentation.

Segmenta os pares sample/outcome por janela intradiaria e por dia de sessao para
impedir que medias gerais escondam desempenho dependente do horario.

A camada e offline/passiva e nao altera AnalysisContext, Strategy, Score, Risk,
Decision ou execucao.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time

from analysis.replay.book_diagnostics_outcome_analyzer import (
    BookDiagnosticsOutcomeAnalyzer,
)


class BookDiagnosticsSessionAnalyzer:
    """Session-aware aggregation for passive BookDiagnostics replay research."""

    VERSION = "RC13-SESSION-SEGMENTATION"

    DEFAULT_WINDOWS = (
        ("OPENING", time(9, 0), time(10, 30)),
        ("MID_MORNING", time(10, 30), time(12, 0)),
        ("LUNCH", time(12, 0), time(14, 0)),
        ("AFTERNOON", time(14, 0), time(16, 30)),
        ("CLOSING", time(16, 30), time(18, 0)),
    )

    def __init__(self, windows=None):
        self.windows = tuple(windows or self.DEFAULT_WINDOWS)
        self.outcome_analyzer = BookDiagnosticsOutcomeAnalyzer()

    def analyze(self, paired_records) -> dict:
        records = list(paired_records or [])
        return {
            "version": self.VERSION,
            "overall": self.outcome_analyzer._metrics(records),
            "by_intraday_window": self._group_by_window(records),
            "by_session_date": self._group_by_session_date(records),
            "by_weekday": self._group_by_weekday(records),
            "by_window_and_state": self._group_by_window_and_state(records),
        }

    def promotion_session_metrics(
        self,
        paired_records,
        *,
        book_state: str | None = None,
        intraday_window: str | None = None,
    ) -> list[dict]:
        """Return one metrics dict per trading date for RC12 stability checks."""
        records = list(paired_records or [])
        filtered = []
        for record in records:
            sample, _ = self.outcome_analyzer._split(record)
            if book_state is not None and str(sample.book_state) != str(book_state):
                continue
            if intraday_window is not None:
                dt = self._parse_timestamp(sample.timestamp)
                if self._window_name(dt) != intraday_window:
                    continue
            filtered.append(record)

        grouped = self._bucket(filtered, self._session_date_key)
        return [
            {"session_date": key, **self.outcome_analyzer._metrics(value)}
            for key, value in sorted(grouped.items())
            if key != "UNKNOWN"
        ]

    def _group_by_window(self, records) -> dict:
        grouped = self._bucket(records, self._window_key)
        return {
            key: self.outcome_analyzer._metrics(value)
            for key, value in sorted(grouped.items())
        }

    def _group_by_session_date(self, records) -> dict:
        grouped = self._bucket(records, self._session_date_key)
        return {
            key: self.outcome_analyzer._metrics(value)
            for key, value in sorted(grouped.items())
        }

    def _group_by_weekday(self, records) -> dict:
        grouped = self._bucket(records, self._weekday_key)
        return {
            key: self.outcome_analyzer._metrics(value)
            for key, value in sorted(grouped.items())
        }

    def _group_by_window_and_state(self, records) -> dict:
        grouped = defaultdict(list)
        for record in records:
            sample, _ = self.outcome_analyzer._split(record)
            dt = self._parse_timestamp(sample.timestamp)
            window = self._window_name(dt)
            state = str(getattr(sample, "book_state", "UNKNOWN") or "UNKNOWN")
            grouped[f"{window}|{state}"].append(record)
        return {
            key: self.outcome_analyzer._metrics(value)
            for key, value in sorted(grouped.items())
        }

    def _bucket(self, records, key_function):
        buckets = defaultdict(list)
        for record in records:
            sample, _ = self.outcome_analyzer._split(record)
            buckets[key_function(sample)].append(record)
        return buckets

    def _window_key(self, sample) -> str:
        return self._window_name(self._parse_timestamp(sample.timestamp))

    def _session_date_key(self, sample) -> str:
        dt = self._parse_timestamp(sample.timestamp)
        return dt.date().isoformat() if dt is not None else "UNKNOWN"

    def _weekday_key(self, sample) -> str:
        dt = self._parse_timestamp(sample.timestamp)
        return dt.strftime("%A").upper() if dt is not None else "UNKNOWN"

    def _window_name(self, dt: datetime | None) -> str:
        if dt is None:
            return "UNKNOWN"
        current = dt.time()
        for name, start, end in self.windows:
            if start <= current < end:
                return str(name)
        return "OUTSIDE_REGULAR_WINDOWS"

    @staticmethod
    def _parse_timestamp(value) -> datetime | None:
        if isinstance(value, datetime):
            return value
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
