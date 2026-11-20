"""Deterministic source-local deduplication that retains every distinct variant."""

from enum import Enum

from .event_model import EventRecord


class DeduplicationResult(str, Enum):
    ADDED = "ADDED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"


class EventDeduplicator:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, int], set[EventRecord]] = {}

    def ingest(self, record: EventRecord) -> DeduplicationResult:
        if type(record) is not EventRecord:
            raise TypeError("ingest requires an EventRecord")
        variants = self._records.setdefault(record.key, set())
        if record in variants:
            return DeduplicationResult.DUPLICATE
        result = DeduplicationResult.CONFLICT if variants else DeduplicationResult.ADDED
        variants.add(record)
        return result

    def history(self) -> tuple[EventRecord, ...]:
        """Return a stable, immutable view, including revisions and conflicts."""
        return tuple(
            record
            for key in sorted(self._records)
            for record in sorted(self._records[key], key=repr)
        )

    def conflicts(self) -> tuple[tuple[str, str, int], ...]:
        return tuple(sorted(key for key, variants in self._records.items() if len(variants) > 1))
