"""In-memory registry of synthetic source fixtures and declared capabilities."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .event_model import EventCategory, EventRecord, _utc


class SourceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICTING = "CONFLICTING"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True, slots=True)
class SourceFixture:
    source_id: str
    capabilities: frozenset[EventCategory]
    status: SourceStatus
    records: tuple[EventRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.source_id) is not str or not self.source_id.strip() or self.source_id != self.source_id.strip():
            raise ValueError("source_id requires a nonempty, trimmed string")
        if not isinstance(self.status, SourceStatus):
            raise ValueError("status requires a SourceStatus")
        if type(self.capabilities) not in (set, frozenset, list, tuple):
            raise ValueError("capabilities require a collection of categories")
        if any(not isinstance(category, EventCategory) for category in self.capabilities):
            raise ValueError("capabilities must contain EventCategory values")
        capabilities = frozenset(self.capabilities)
        if type(self.records) not in (tuple, list):
            raise ValueError("records require an in-memory fixture list or tuple")
        records = tuple(self.records)
        for record in records:
            if type(record) is not EventRecord or record.source_id != self.source_id:
                raise ValueError("fixture records must belong to the declared source")
            if record.category not in capabilities:
                raise ValueError("record category exceeds the declared source capabilities")
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "records", records)


class SourceRegistry:
    """Looks up local fixtures without transport, credentials or file loading."""

    def __init__(self, fixtures: tuple[SourceFixture, ...] = ()) -> None:
        self._sources: dict[str, SourceFixture] = {}
        for fixture in fixtures:
            if type(fixture) is not SourceFixture:
                raise TypeError("registry accepts SourceFixture values")
            if fixture.source_id in self._sources:
                raise ValueError(f"duplicate source fixture: {fixture.source_id}")
            self._sources[fixture.source_id] = fixture

    def get(self, source_id: str) -> SourceFixture:
        return self._sources[source_id]

    def records_as_of(self, source_id: str, as_of: datetime) -> tuple[EventRecord, ...]:
        as_of = _utc(as_of, "as_of")
        fixture = self.get(source_id)
        if fixture.status is not SourceStatus.AVAILABLE:
            return ()
        return tuple(record for record in fixture.records if record.is_available_at(as_of))
