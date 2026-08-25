"""Resumo factual do diário psicológico da sessão (RC22)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from psychology.trader_psychology_session_journal import (
    TraderPsychologyJournalEntry,
)
from psychology.trader_psychology_session_time import (
    to_session_iso,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionSummary:
    status: str
    total_cycles: int
    neutral_cycles: int
    attention_cycles: int
    pause_recommended_cycles: int
    linked_evidence_cycles: int
    unique_evidence_trade_ids: tuple[str, ...]
    signal_counts: tuple[tuple[str, int], ...]
    dominant_signal_code: str | None
    voice_delivered_cycles: int
    voice_suppressed_cycles: int
    voice_failed_cycles: int
    first_sequence: int | None
    last_sequence: int | None
    started_at: datetime | None
    updated_at: datetime | None
    total_observations: int = 0
    longest_unchanged_observations: int = 0
    session_date: str | None = None
    session_timezone: str | None = None
    session_id: str | None = None
    prior_session_entries_ignored: int = 0
    prior_session_observations_ignored: int = 0
    observed_span_seconds: float = 0.0
    started_at_local: str | None = None
    updated_at_local: str | None = None
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionSummarizer:
    """Agrega somente fatos já registrados no diário."""

    NAME = "TraderPsychologySessionSummarizer"
    VERSION = "RC30"

    def summarize(self, entries):
        if not isinstance(entries, (list, tuple)):
            raise TypeError("entries deve ser lista ou tupla.")
        if any(
            not isinstance(entry, TraderPsychologyJournalEntry)
            for entry in entries
        ):
            raise TypeError("entries contém item incompatível.")

        all_ordered = tuple(
            sorted(entries, key=lambda entry: entry.sequence)
        )
        if not all_ordered:
            return TraderPsychologySessionSummary(
                status="EMPTY",
                total_cycles=0,
                neutral_cycles=0,
                attention_cycles=0,
                pause_recommended_cycles=0,
                linked_evidence_cycles=0,
                unique_evidence_trade_ids=(),
                signal_counts=(),
                dominant_signal_code=None,
                voice_delivered_cycles=0,
                voice_suppressed_cycles=0,
                voice_failed_cycles=0,
                first_sequence=None,
                last_sequence=None,
                started_at=None,
                updated_at=None,
                total_observations=0,
                longest_unchanged_observations=0,
                session_date=None,
                session_timezone=None,
                session_id=None,
                prior_session_entries_ignored=0,
                prior_session_observations_ignored=0,
                observed_span_seconds=0.0,
                started_at_local=None,
                updated_at_local=None,
            )

        latest_entry = all_ordered[-1]
        latest_date = self._session_date(latest_entry)
        latest_session_id = self._session_id(latest_entry)
        ordered = tuple(
            entry
            for entry in all_ordered
            if self._session_id(entry) == latest_session_id
        )
        ignored = tuple(
            entry
            for entry in all_ordered
            if self._session_id(entry) != latest_session_id
        )
        prior_ignored = len(ignored)
        prior_observations_ignored = sum(
            entry.observation_count
            for entry in ignored
        )

        counts = Counter(
            code
            for entry in ordered
            for code in entry.signal_codes
        )
        signal_counts = tuple(
            sorted(
                counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        )
        started_at = ordered[0].recorded_at
        updated_at = (
            ordered[-1].last_observed_at
            or ordered[-1].recorded_at
        )
        observed_span_seconds = max(
            0.0,
            (updated_at - started_at).total_seconds(),
        )
        evidence_trade_ids = tuple(
            dict.fromkeys(
                trade_id
                for entry in ordered
                for trade_id in entry.evidence_trade_ids
            )
        )
        return TraderPsychologySessionSummary(
            status="AVAILABLE",
            total_cycles=len(ordered),
            neutral_cycles=sum(
                entry.status == "NEUTRAL"
                for entry in ordered
            ),
            attention_cycles=sum(
                entry.status == "ATTENTION"
                for entry in ordered
            ),
            pause_recommended_cycles=sum(
                entry.pause_recommended
                for entry in ordered
            ),
            linked_evidence_cycles=sum(
                entry.evidence_status == "LINKED"
                for entry in ordered
            ),
            unique_evidence_trade_ids=evidence_trade_ids,
            signal_counts=signal_counts,
            dominant_signal_code=(
                signal_counts[0][0]
                if signal_counts
                else None
            ),
            voice_delivered_cycles=sum(
                entry.voice_status == "DELIVERED"
                for entry in ordered
            ),
            voice_suppressed_cycles=sum(
                entry.voice_status == "COOLDOWN"
                for entry in ordered
            ),
            voice_failed_cycles=sum(
                entry.voice_status == "FAILED"
                for entry in ordered
            ),
            first_sequence=ordered[0].sequence,
            last_sequence=ordered[-1].sequence,
            started_at=started_at,
            updated_at=updated_at,
            total_observations=sum(
                entry.observation_count
                for entry in ordered
            ),
            longest_unchanged_observations=max(
                entry.observation_count
                for entry in ordered
            ),
            session_date=latest_date,
            session_timezone=ordered[-1].session_timezone,
            session_id=latest_session_id,
            prior_session_entries_ignored=prior_ignored,
            prior_session_observations_ignored=(
                prior_observations_ignored
            ),
            observed_span_seconds=observed_span_seconds,
            started_at_local=to_session_iso(
                started_at,
                ordered[-1].session_timezone,
            ),
            updated_at_local=to_session_iso(
                updated_at,
                ordered[-1].session_timezone,
            ),
        )

    @classmethod
    def _session_id(cls, entry):
        return (
            entry.session_id
            or (
                f"{cls._session_date(entry)}"
                f"@{entry.session_timezone}"
            )
        )

    @staticmethod
    def _session_date(entry):
        return (
            entry.session_date
            or entry.recorded_at.date().isoformat()
        )
