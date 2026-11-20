"""Offline evidence records for political market intelligence."""

from .event_deduplicator import DeduplicationResult, EventDeduplicator
from .event_model import EventCategory, EventRecord, EvidenceReference, FactStatus
from .source_registry import SourceFixture, SourceRegistry, SourceStatus

__all__ = [
    "DeduplicationResult",
    "EventCategory",
    "EventDeduplicator",
    "EventRecord",
    "EvidenceReference",
    "FactStatus",
    "SourceFixture",
    "SourceRegistry",
    "SourceStatus",
]
