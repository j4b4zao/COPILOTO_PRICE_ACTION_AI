"""Replay simulated transcript revisions with explicit verification boundaries."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .event_deduplicator import EventDeduplicator
from .event_model import (
    EventCategory, EventRecord, EvidenceReference, _utc, _validate_identity,
)
from .source_registry import SourceRegistry, SourceStatus


class SpeechStatus(str, Enum):
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    VERIFIED = "VERIFIED"
    CONFLICTING = "CONFLICTING"
    CORRECTED = "CORRECTED"


@dataclass(frozen=True, slots=True, kw_only=True)
class SpeechFixture:
    source_id: str
    event_id: str
    revision: int
    authority: str
    associated_event_id: str
    status: SpeechStatus
    speech_at: datetime
    published_at: datetime
    received_at: datetime
    provenance: str
    evidence: tuple[EvidenceReference, ...] = ()
    text: str = ""
    verified_at: datetime | None = None
    record: EventRecord | None = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        _validate_identity(self.source_id, self.event_id, self.revision)
        if not isinstance(self.status, SpeechStatus):
            raise ValueError("status requires a SpeechStatus")
        for name in ("authority", "associated_event_id", "provenance"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{name} requires a nonempty string")
        pending = self.status is SpeechStatus.PENDING
        if type(self.text) is not str or pending == bool(self.text.strip()):
            raise ValueError("pending transcripts require empty text; other statuses require text")
        for name in ("speech_at", "published_at", "received_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.received_at < self.published_at:
            raise ValueError("received_at precedes published_at")
        if not pending and self.speech_at > self.published_at:
            raise ValueError("transcript publication precedes the speech")
        if type(self.evidence) not in (list, tuple) or any(
            type(ref) is not EvidenceReference for ref in self.evidence
        ):
            raise ValueError("evidence requires a collection of EvidenceReference values")
        refs = tuple(sorted(self.evidence, key=lambda ref: ref.key))
        keys = {ref.key for ref in refs}
        if len(keys) != len(refs) or (self.source_id, self.event_id, self.revision) in keys:
            raise ValueError("evidence references must be distinct and cannot reference this revision")
        object.__setattr__(self, "evidence", refs)
        if self.status in (SpeechStatus.VERIFIED, SpeechStatus.CORRECTED):
            if self.status is SpeechStatus.CORRECTED and self.revision < 2:
                raise ValueError("a correction requires a new revision")
            record = EventRecord(
                source_id=self.source_id, event_id=self.event_id, revision=self.revision,
                category=EventCategory.VERIFIED_TRANSCRIPT, provenance=self.provenance,
                content=self.text, event_time=self.speech_at, published_at=self.published_at,
                received_at=self.received_at, verified_at=self.verified_at, evidence=refs,
            )
            object.__setattr__(self, "verified_at", record.verified_at)
            object.__setattr__(self, "record", record)
        elif self.verified_at is not None:
            raise ValueError("only verified and corrected transcripts may have verified_at")

    @property
    def available_at(self) -> datetime:
        if self.record is not None:
            return self.record.available_at
        return max((self.received_at, *(ref.available_at for ref in self.evidence)))


@dataclass(frozen=True, slots=True)
class SpeechSnapshot:
    history: tuple[SpeechFixture, ...]
    current: tuple[SpeechFixture, ...]
    verified_records: tuple[EventRecord, ...]
    conflicts: tuple[str, ...]  # Associated event IDs, without an automatic winner.


class SpeechMonitor:
    """Expose transcript workflow separately from verified A2 records."""

    def __init__(self, sources: SourceRegistry) -> None:
        self._sources = sources

    def collect(self, fixtures: tuple[SpeechFixture, ...], *, as_of: datetime) -> SpeechSnapshot:
        as_of = _utc(as_of, "as_of")
        variants = {}
        source_conflicts = set()
        for fixture in fixtures:
            if type(fixture) is not SpeechFixture:
                raise TypeError("collect requires SpeechFixture values")
            source = self._sources.get(fixture.source_id)
            if (
                source.status in (SourceStatus.AVAILABLE, SourceStatus.CONFLICTING)
                and EventCategory.VERIFIED_TRANSCRIPT in source.capabilities
                and fixture.available_at <= as_of
            ):
                key = fixture.source_id, fixture.event_id, fixture.revision
                variants.setdefault(key, set()).add(fixture)
                if source.status is SourceStatus.CONFLICTING:
                    source_conflicts.add(fixture.associated_event_id)

        history = tuple(
            fixture for key in sorted(variants) for fixture in sorted(variants[key], key=repr)
        )
        latest = {}
        for fixture in history:
            latest[fixture.source_id, fixture.event_id] = fixture.revision
        current = tuple(
            f for f in history if f.revision == latest[f.source_id, f.event_id]
        )
        conflicts = {
            fixture.associated_event_id
            for entries in variants.values() if len(entries) > 1
            for fixture in entries
        }
        conflicts.update(source_conflicts)
        conflicts.update(
            f.associated_event_id for f in history if f.status is SpeechStatus.CONFLICTING
        )
        claims = {}
        for fixture in current:
            if fixture.record is not None:
                claims.setdefault(fixture.associated_event_id, set()).add(
                    (fixture.authority, fixture.speech_at, fixture.text)
                )
        conflicts.update(event_id for event_id, texts in claims.items() if len(texts) > 1)

        dedup = EventDeduplicator()
        for fixture in current:
            if fixture.record is not None and fixture.associated_event_id not in conflicts:
                dedup.ingest(fixture.record)
        return SpeechSnapshot(history, current, dedup.history(), tuple(sorted(conflicts)))
