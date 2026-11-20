"""Immutable, time-aware records for observations and their evidence."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re


class EventCategory(str, Enum):
    CONFIRMED_FACT = "CONFIRMED_FACT"
    VERIFIED_TRANSCRIPT = "VERIFIED_TRANSCRIPT"
    AI_INTERPRETATION = "AI_INTERPRETATION"
    IMPACT_HYPOTHESIS = "IMPACT_HYPOTHESIS"
    OBSERVED_REACTION = "OBSERVED_REACTION"


class FactStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    OCCURRED = "OCCURRED"


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} requires a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _validate_identity(source_id: str, event_id: str, revision: int) -> None:
    for name, value in (("source_id", source_id), ("event_id", event_id)):
        if type(value) is not str or not value.strip() or value != value.strip():
            raise ValueError(f"{name} requires a nonempty, trimmed string")
    if type(revision) is not int or revision < 1:
        raise ValueError("revision requires a positive integer")


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    source_id: str
    event_id: str
    revision: int
    available_at: datetime

    def __post_init__(self) -> None:
        _validate_identity(self.source_id, self.event_id, self.revision)
        object.__setattr__(self, "available_at", _utc(self.available_at, "available_at"))

    @property
    def key(self) -> tuple[str, str, int]:
        return self.source_id, self.event_id, self.revision


@dataclass(frozen=True, slots=True, kw_only=True)
class EventRecord:
    """A source-scoped event revision with separately recorded clock times.

    A scheduled fact confirms the schedule. An occurred fact confirms the event.
    """

    source_id: str
    event_id: str
    revision: int
    category: EventCategory
    provenance: str
    content: str
    event_time: datetime
    published_at: datetime
    received_at: datetime
    evidence: tuple[EvidenceReference, ...]
    verified_at: datetime | None = None
    contract: str | None = None
    fact_status: FactStatus | None = None

    def __post_init__(self) -> None:
        _validate_identity(self.source_id, self.event_id, self.revision)
        if not isinstance(self.category, EventCategory):
            raise ValueError("category requires an EventCategory")
        for name in ("provenance", "content"):
            value = getattr(self, name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{name} requires a nonempty string")

        for name in ("event_time", "published_at", "received_at"):
            object.__setattr__(self, name, _utc(getattr(self, name), name))
        if self.verified_at is not None:
            object.__setattr__(self, "verified_at", _utc(self.verified_at, "verified_at"))
        if self.received_at < self.published_at:
            raise ValueError("received_at precedes published_at")
        if self.verified_at is not None and self.verified_at < self.received_at:
            raise ValueError("verified_at precedes received_at")

        if type(self.evidence) not in (tuple, list):
            raise ValueError("evidence requires a tuple or list of references")
        if not self.evidence or any(type(ref) is not EvidenceReference for ref in self.evidence):
            raise ValueError("evidence requires at least one EvidenceReference")
        evidence = tuple(sorted(self.evidence, key=lambda ref: ref.key))
        keys = {ref.key for ref in evidence}
        if len(keys) != len(evidence) or self.key in keys:
            raise ValueError("evidence references must be distinct and cannot reference this revision")
        object.__setattr__(self, "evidence", evidence)

        if self.category is EventCategory.CONFIRMED_FACT:
            if not isinstance(self.fact_status, FactStatus):
                raise ValueError("confirmed facts require an explicit fact_status")
        elif self.fact_status is not None:
            raise ValueError("fact_status applies only to confirmed facts")

        if self.category in (EventCategory.CONFIRMED_FACT, EventCategory.VERIFIED_TRANSCRIPT):
            if self.verified_at is None:
                raise ValueError("facts and transcripts require verified_at")
            if any(ref.available_at > self.verified_at for ref in evidence):
                raise ValueError("verification precedes availability of its evidence")
        if (
            self.fact_status is FactStatus.OCCURRED
            or self.category in (EventCategory.VERIFIED_TRANSCRIPT, EventCategory.OBSERVED_REACTION)
        ) and self.event_time > self.published_at:
            raise ValueError("an occurrence, transcript or observation cannot precede its event")

        if self.contract is not None:
            if type(self.contract) is not str or not re.fullmatch(
                r"(?:WIN|WDO)[FGHJKMNQUVXZ][0-9]{2}", self.contract
            ):
                raise ValueError("contract requires a full WIN/WDO symbol")
        elif self.category is EventCategory.OBSERVED_REACTION:
            raise ValueError("an observed market reaction requires a contract")

    @property
    def key(self) -> tuple[str, str, int]:
        return self.source_id, self.event_id, self.revision

    @property
    def available_at(self) -> datetime:
        return max(self.verified_at or self.received_at, *(ref.available_at for ref in self.evidence))

    def is_available_at(self, as_of: datetime) -> bool:
        return _utc(as_of, "as_of") >= self.available_at
