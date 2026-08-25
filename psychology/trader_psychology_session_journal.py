"""Diário observacional e limitado da sessão psicológica (RC21)."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from psychology.trader_psychology_runtime import (
    TraderPsychologyRuntimeResult,
)


@dataclass(frozen=True, slots=True)
class TraderPsychologyJournalEntry:
    sequence: int
    recorded_at: datetime
    status: str
    signal_codes: tuple[str, ...]
    pause_recommended: bool
    pause_reason_codes: tuple[str, ...]
    coaching_codes: tuple[str, ...]
    evidence_status: str | None
    evidence_audit_sequences: tuple[int, ...]
    evidence_trade_ids: tuple[str, ...]
    voice_status: str
    voice_delivery_codes: tuple[str, ...]
    observation_count: int = 1
    last_observed_at: datetime | None = None
    session_date: str = ""
    session_timezone: str = "UTC"
    observational_only: bool = True
    score_influence_allowed: bool = False
    order_execution_allowed: bool = False
    operational_block_allowed: bool = False


class TraderPsychologySessionJournal:
    """Mantém somente projeções psicológicas; não persiste automaticamente."""

    NAME = "TraderPsychologySessionJournal"
    VERSION = "RC21"

    def __init__(
        self,
        *,
        max_entries=500,
        clock=None,
        deduplicate_unchanged=False,
        session_timezone="UTC",
    ):
        if isinstance(max_entries, bool) or not isinstance(
            max_entries,
            int,
        ):
            raise TypeError("max_entries deve ser inteiro.")
        if not 1 <= max_entries <= 10000:
            raise ValueError(
                "max_entries deve ficar entre 1 e 10000."
            )
        if not isinstance(deduplicate_unchanged, bool):
            raise TypeError(
                "deduplicate_unchanged deve ser booleano."
            )
        if not isinstance(session_timezone, str) or not (
            session_timezone.strip()
        ):
            raise TypeError(
                "session_timezone deve ser string não vazia."
            )
        timezone_name = session_timezone.strip()
        try:
            timezone_value = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            if timezone_name == "America/Sao_Paulo":
                timezone_value = timezone(
                    timedelta(hours=-3),
                    name="America/Sao_Paulo",
                )
            else:
                raise ValueError(
                    "session_timezone desconhecido."
                ) from exc
        self.max_entries = max_entries
        self.deduplicate_unchanged = deduplicate_unchanged
        self.session_timezone = timezone_name
        self._session_timezone = timezone_value
        self.clock = clock or (
            lambda: datetime.now(timezone.utc)
        )
        if not callable(self.clock):
            raise TypeError("clock deve ser chamável.")
        self._entries = deque(maxlen=max_entries)
        self._sequence = 0
        self._lock = Lock()

    @property
    def entries(self):
        with self._lock:
            return tuple(self._entries)

    def record(self, runtime_result):
        if not isinstance(
            runtime_result,
            TraderPsychologyRuntimeResult,
        ):
            raise TypeError(
                "runtime_result deve ser "
                "TraderPsychologyRuntimeResult."
            )
        recorded_at = self.clock()
        if (
            not isinstance(recorded_at, datetime)
            or recorded_at.tzinfo is None
            or recorded_at.utcoffset() is None
        ):
            raise TypeError(
                "clock deve retornar datetime com timezone."
            )

        evidence = runtime_result.evidence
        links = evidence.links if evidence is not None else ()
        audit_sequences = tuple(
            dict.fromkeys(
                sequence
                for link in links
                for sequence in link.audit_sequences
            )
        )
        trade_ids = tuple(
            dict.fromkeys(
                trade_id
                for link in links
                for trade_id in link.trade_ids
            )
        )

        with self._lock:
            candidate = TraderPsychologyJournalEntry(
                sequence=self._sequence + 1,
                recorded_at=recorded_at,
                status=runtime_result.status,
                signal_codes=tuple(
                    signal.code
                    for signal in runtime_result.psychology.signals
                ),
                pause_recommended=runtime_result.pause_recommended,
                pause_reason_codes=tuple(
                    runtime_result.psychology.pause_reason_codes
                ),
                coaching_codes=tuple(
                    message.code
                    for message in runtime_result.coaching.messages
                ),
                evidence_status=(
                    evidence.status
                    if evidence is not None
                    else None
                ),
                evidence_audit_sequences=audit_sequences,
                evidence_trade_ids=trade_ids,
                voice_status=runtime_result.voice.status,
                voice_delivery_codes=tuple(
                    delivery.code
                    for delivery in runtime_result.voice.deliveries
                ),
                last_observed_at=recorded_at,
                session_date=(
                    recorded_at.astimezone(
                        self._session_timezone
                    ).date().isoformat()
                ),
                session_timezone=self.session_timezone,
            )
            if (
                self.deduplicate_unchanged
                and self._entries
                and self._fingerprint(self._entries[-1])
                == self._fingerprint(candidate)
            ):
                repeated = replace(
                    self._entries[-1],
                    observation_count=(
                        self._entries[-1].observation_count + 1
                    ),
                    last_observed_at=recorded_at,
                )
                self._entries[-1] = repeated
                return repeated

            self._sequence += 1
            self._entries.append(candidate)
            return candidate

    @staticmethod
    def _fingerprint(entry):
        return (
            entry.session_date,
            entry.status,
            entry.signal_codes,
            entry.pause_recommended,
            entry.pause_reason_codes,
            entry.coaching_codes,
            entry.evidence_status,
            entry.evidence_audit_sequences,
            entry.evidence_trade_ids,
            entry.voice_status,
            entry.voice_delivery_codes,
        )

    def clear(self):
        with self._lock:
            removed = len(self._entries)
            self._entries.clear()
            return removed

    def __len__(self):
        with self._lock:
            return len(self._entries)
