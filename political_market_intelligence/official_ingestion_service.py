"""PMI-RC2-A5: deterministic, offline-only ingestion of local document dictionaries.

Does not read files, use network, authenticate sources, promote evidence, or trade.
Each batch is atomic: any invalid input or conflicting revision rejects the batch.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .official_document_normalizer import (
    DocumentObservation, OfficialDocumentNormalizer, _utc,
)
from .official_source_catalog import OfficialSourceCatalog


class IngestionDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    REPLAY = "REPLAY"


@dataclass(frozen=True, slots=True)
class IngestionReceipt:
    source_id: str
    document_id: str
    revision: int
    content_sha256: str
    disposition: IngestionDisposition


@dataclass(frozen=True, slots=True)
class IngestionBatchResult:
    as_of: datetime
    receipts: tuple[IngestionReceipt, ...]
    documents: tuple[DocumentObservation, ...]
    total_documents: int


class OfficialIngestionService:
    """In-memory, single-process state; never persists or performs I/O."""

    def __init__(self, catalog: OfficialSourceCatalog) -> None:
        if type(catalog) is not OfficialSourceCatalog:
            raise TypeError("catalog must be OfficialSourceCatalog")
        self._normalizer = OfficialDocumentNormalizer(catalog)
        self._documents: dict[tuple[str, str, int], DocumentObservation] = {}
        self._last_as_of: datetime | None = None

    def ingest(self, payloads: tuple[dict, ...], *, as_of: datetime) -> IngestionBatchResult:
        """Normalize and atomically ingest a batch, rejecting revision conflicts.

        An identical replay is idempotent. Earlier cutoffs are rejected to avoid
        misleading snapshots. Cross-revision chronology is checked per document.
        """
        cutoff = _utc(as_of, "as_of")
        if self._last_as_of is not None and cutoff < self._last_as_of:
            raise ValueError("as_of cannot move backwards")
        incoming = self._normalizer.normalize_many(payloads, as_of=cutoff)
        staged = dict(self._documents)
        receipts = []
        for doc in incoming:
            previous = staged.get(doc.key)
            if previous is not None:
                if previous != doc:
                    raise ValueError(f"conflicting replay: {doc.key}")
                disposition = IngestionDisposition.REPLAY
            else:
                for old in staged.values():
                    if (old.source_id, old.document_id) != (doc.source_id, doc.document_id):
                        continue
                    if old.revision < doc.revision and old.received_at > doc.received_at:
                        raise ValueError("higher revision received before lower revision")
                    if old.revision > doc.revision and old.received_at < doc.received_at:
                        raise ValueError("lower revision received after higher revision")
                staged[doc.key] = doc
                disposition = IngestionDisposition.ACCEPTED
            receipts.append(IngestionReceipt(doc.source_id, doc.document_id,
                                             doc.revision, doc.content_sha256,
                                             disposition))
        self._documents = staged
        self._last_as_of = cutoff
        return IngestionBatchResult(cutoff, tuple(receipts),
                                    tuple(staged[key] for key in sorted(staged)),
                                    len(staged))

    def snapshot(self, *, as_of: datetime) -> tuple[DocumentObservation, ...]:
        cutoff = _utc(as_of, "as_of")
        return tuple(doc for key, doc in sorted(self._documents.items())
                     if doc.is_available_at(cutoff))
