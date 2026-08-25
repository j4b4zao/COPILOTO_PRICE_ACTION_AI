"""Catálogo readonly das sessões psicológicas preservadas (RC38)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from psychology.trader_psychology_session_journal import (
    TraderPsychologyJournalEntry,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalogItem:
    session_id: str
    session_date: str
    session_timezone: str
    total_entries: int
    total_observations: int
    first_sequence: int
    last_sequence: int
    started_at: datetime
    updated_at: datetime
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


@dataclass(frozen=True, slots=True)
class TraderPsychologySessionCatalog:
    status: str
    total_sessions: int
    latest_session_id: str | None
    sessions: tuple[TraderPsychologySessionCatalogItem, ...]
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionCatalogBuilder:
    """Lista metadados factuais; não compara sessões."""

    NAME = "TraderPsychologySessionCatalogBuilder"
    VERSION = "RC38"

    def build(self, entries):
        if not isinstance(entries, (list, tuple)):
            raise TypeError("entries deve ser lista ou tupla.")
        if any(
            not isinstance(entry, TraderPsychologyJournalEntry)
            for entry in entries
        ):
            raise TypeError("entries contém item incompatível.")

        ordered = tuple(
            sorted(entries, key=lambda entry: entry.sequence)
        )
        if not ordered:
            return TraderPsychologySessionCatalog(
                status="EMPTY",
                total_sessions=0,
                latest_session_id=None,
                sessions=(),
            )

        groups = {}
        for entry in ordered:
            session_id = self._session_id(entry)
            groups.setdefault(session_id, []).append(entry)

        items = tuple(
            sorted(
                (
                    self._item(session_id, values)
                    for session_id, values in groups.items()
                ),
                key=lambda item: item.last_sequence,
                reverse=True,
            )
        )
        return TraderPsychologySessionCatalog(
            status="AVAILABLE",
            total_sessions=len(items),
            latest_session_id=items[0].session_id,
            sessions=items,
        )

    @staticmethod
    def _session_id(entry):
        session_date = (
            entry.session_date
            or entry.recorded_at.date().isoformat()
        )
        return (
            entry.session_id
            or f"{session_date}@{entry.session_timezone}"
        )

    @staticmethod
    def _item(session_id, entries):
        first = entries[0]
        last = entries[-1]
        updated_at = (
            last.last_observed_at
            or last.recorded_at
        )
        return TraderPsychologySessionCatalogItem(
            session_id=session_id,
            session_date=(
                last.session_date
                or last.recorded_at.date().isoformat()
            ),
            session_timezone=last.session_timezone,
            total_entries=len(entries),
            total_observations=sum(
                entry.observation_count
                for entry in entries
            ),
            first_sequence=first.sequence,
            last_sequence=last.sequence,
            started_at=first.recorded_at,
            updated_at=updated_at,
        )
