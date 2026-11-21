"""PMI-RC2-A4: strict offline normalization of unverified document observations.

No networking, source authentication, EventRecord promotion or trading actions.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
import re

from .official_source_catalog import OfficialSourceCatalog
from .source_registry import SourceStatus


class DocumentState(str, Enum):
    UNVERIFIED = "UNVERIFIED"


def _utc(value: datetime, field: str) -> datetime:
    if type(value) is not datetime or value.utcoffset() is None:
        raise ValueError(f"{field} requires timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _identifier(value: str, field: str) -> str:
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", value):
        raise ValueError(f"invalid {field}")
    return value


@dataclass(frozen=True, slots=True, kw_only=True)
class DocumentObservation:
    source_id: str
    document_id: str
    revision: int
    title: str
    content: str
    published_at: datetime
    received_at: datetime
    state: DocumentState = DocumentState.UNVERIFIED
    content_sha256: str = ""

    def __post_init__(self) -> None:
        _identifier(self.source_id, "source_id")
        _identifier(self.document_id, "document_id")
        if type(self.revision) is not int or self.revision < 1:
            raise ValueError("revision requires positive integer")
        for field in ("title", "content"):
            value = getattr(self, field)
            if type(value) is not str or not value.strip() or len(value) > (500 if field == "title" else 100_000):
                raise ValueError(f"invalid {field}")
        published = _utc(self.published_at, "published_at")
        received = _utc(self.received_at, "received_at")
        if received < published:
            raise ValueError("received_at precedes published_at")
        if self.state is not DocumentState.UNVERIFIED:
            raise ValueError("documents cannot be promoted to verified in A4")
        digest = sha256(self.content.encode("utf-8")).hexdigest()
        if self.content_sha256 and self.content_sha256 != digest:
            raise ValueError("content hash mismatch")
        object.__setattr__(self, "published_at", published)
        object.__setattr__(self, "received_at", received)
        object.__setattr__(self, "content_sha256", digest)

    @property
    def key(self) -> tuple[str, str, int]:
        return self.source_id, self.document_id, self.revision

    def is_available_at(self, as_of: datetime) -> bool:
        return self.received_at <= _utc(as_of, "as_of")


class OfficialDocumentNormalizer:
    """Normalize explicit local dictionaries; never fetch or verify sources."""

    REQUIRED = frozenset({
        "source_id", "document_id", "revision", "title", "content",
        "published_at", "received_at",
    })

    def __init__(self, catalog: OfficialSourceCatalog) -> None:
        if type(catalog) is not OfficialSourceCatalog:
            raise TypeError("catalog must be OfficialSourceCatalog")
        self._catalog = catalog

    def normalize(self, payload: dict, *, as_of: datetime) -> DocumentObservation:
        cutoff = _utc(as_of, "as_of")
        if type(payload) is not dict or set(payload) != self.REQUIRED:
            raise ValueError("payload must contain exactly required fields")
        source = self._catalog.get(_identifier(payload["source_id"], "source_id"))
        if source.status is not SourceStatus.UNVERIFIED or source.collection_enabled:
            raise ValueError("source is not offline-unverified")
        result = DocumentObservation(**payload)
        if not result.is_available_at(cutoff):
            raise ValueError("document not yet received at cutoff")
        return result

    def normalize_many(self, payloads: tuple[dict, ...], *, as_of: datetime) -> tuple[DocumentObservation, ...]:
        if type(payloads) not in (tuple, list):
            raise TypeError("payloads must be tuple or list")
        results = tuple(self.normalize(payload, as_of=as_of) for payload in payloads)
        keys = [item.key for item in results]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate document revision")
        return tuple(sorted(results, key=lambda item: item.key))
