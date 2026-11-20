"""Read-only replay of local agenda notices and occurrence confirmations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from .event_deduplicator import EventDeduplicator
from .event_model import EventCategory, EventRecord, EvidenceReference, FactStatus, _utc
from .source_registry import SourceRegistry, SourceStatus


class AgendaStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"
    OCCURRENCE_CONFIRMED = "OCCURRENCE_CONFIRMED"


@dataclass(frozen=True, slots=True, kw_only=True)
class AgendaFixture:
    source_id: str
    event_id: str
    revision: int
    authority: str
    office: str
    title: str
    status: AgendaStatus
    scheduled_at: datetime
    published_at: datetime
    received_at: datetime
    verified_at: datetime
    provenance: str
    evidence: tuple[EvidenceReference, ...]
    location: str | None = None
    occurred_at: datetime | None = None
    record: EventRecord = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.status, AgendaStatus):
            raise ValueError("status requires an AgendaStatus")
        for name in ("authority", "office", "title", "location"):
            value = getattr(self, name)
            if name == "location" and value is None:
                continue
            if type(value) is not str or not value.strip():
                raise ValueError(f"{name} requires a nonempty string")
        occurred = self.status is AgendaStatus.OCCURRENCE_CONFIRMED
        if occurred != (self.occurred_at is not None):
            raise ValueError("occurred_at is required only for a confirmed occurrence")
        scheduled_at = _utc(self.scheduled_at, "scheduled_at")
        event_time = _utc(self.occurred_at, "occurred_at") if occurred else scheduled_at
        details = {
            "authority": self.authority,
            "office": self.office,
            "title": self.title,
            "location": self.location,
            "status": self.status.value,
            "scheduled_at": scheduled_at.isoformat(),
        }
        record = EventRecord(
            source_id=self.source_id, event_id=self.event_id, revision=self.revision,
            category=EventCategory.CONFIRMED_FACT, provenance=self.provenance,
            content=json.dumps(details, sort_keys=True), event_time=event_time,
            published_at=self.published_at, received_at=self.received_at,
            verified_at=self.verified_at, evidence=self.evidence,
            fact_status=FactStatus.OCCURRED if occurred else FactStatus.SCHEDULED,
        )
        object.__setattr__(self, "scheduled_at", scheduled_at)
        object.__setattr__(self, "occurred_at", event_time if occurred else None)
        for name in ("published_at", "received_at", "verified_at", "evidence"):
            object.__setattr__(self, name, getattr(record, name))
        object.__setattr__(self, "record", record)


@dataclass(frozen=True, slots=True)
class AgendaSnapshot:
    history: tuple[AgendaFixture, ...]
    current: tuple[AgendaFixture, ...]
    conflicts: tuple[str, ...]  # Associated event IDs with unresolved current claims.


class PresidentialAgendaCollector:
    """Project available local notices as of an explicit replay timestamp."""

    def __init__(self, sources: SourceRegistry) -> None:
        self._sources = sources

    def collect(self, fixtures: tuple[AgendaFixture, ...], *, as_of: datetime) -> AgendaSnapshot:
        as_of = _utc(as_of, "as_of")
        by_record = {}
        dedup = EventDeduplicator()
        conflicts = set()
        for fixture in fixtures:
            if type(fixture) is not AgendaFixture:
                raise TypeError("collect requires AgendaFixture values")
            source = self._sources.get(fixture.source_id)
            record = fixture.record
            if (
                source.status in (SourceStatus.AVAILABLE, SourceStatus.CONFLICTING)
                and record.category in source.capabilities
                and record.is_available_at(as_of)
            ):
                dedup.ingest(record)
                by_record[record] = fixture
                if source.status is SourceStatus.CONFLICTING:
                    conflicts.add(fixture.event_id)

        history = tuple(by_record[record] for record in dedup.history())
        latest = {}
        for fixture in history:
            # A2 history is sorted by source, event and revision.
            latest[fixture.record.key[:2]] = fixture.revision
        current = tuple(f for f in history if f.revision == latest[f.record.key[:2]])
        claims = {}
        for fixture in current:
            claims.setdefault(fixture.event_id, set()).add(
                (fixture.status, fixture.scheduled_at, fixture.occurred_at,
                 fixture.authority, fixture.office, fixture.title, fixture.location)
            )
        conflicts.update(event_id for event_id, variants in claims.items() if len(variants) > 1)
        # Retain visible same-revision conflicts even after another revision arrives.
        conflicts.update(event_id for _, event_id, _ in dedup.conflicts())
        return AgendaSnapshot(history, current, tuple(sorted(conflicts)))
