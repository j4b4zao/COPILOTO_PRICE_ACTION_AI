"""PMI-RC2-A5: offline ingestion, atomicity, chronology, and idempotence."""
import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_source_catalog import (
    OfficialSource, OfficialSourceCatalog, OfficialSourceKind,
)
from political_market_intelligence.official_ingestion_service import (
    OfficialIngestionService, IngestionDisposition,
)

T = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)


def payload(**changes):
    data = dict(source_id="test-source", document_id="doc-1", revision=1,
                title="Comunicado", content="Texto local", published_at=T,
                received_at=T + timedelta(minutes=1))
    data.update(changes)
    return data


class OfflineIngestionTests(unittest.TestCase):
    def setUp(self):
        source = OfficialSource(source_id="test-source", institution="Instituicao teste",
                                country_code="BR", kind=OfficialSourceKind.COMMUNICATION,
                                candidate_url="https://example.org/",
                                capabilities=frozenset({EventCategory.CONFIRMED_FACT}))
        self.service = OfficialIngestionService(OfficialSourceCatalog((source,)))
        self.cutoff = T + timedelta(minutes=10)

    def test_accepts_unverified(self):
        result = self.service.ingest((payload(),), as_of=self.cutoff)
        self.assertEqual(result.receipts[0].disposition, IngestionDisposition.ACCEPTED)
        self.assertEqual(result.documents[0].state.value, "UNVERIFIED")
        self.assertEqual(result.total_documents, 1)

    def test_replay_idempotent(self):
        self.service.ingest((payload(),), as_of=self.cutoff)
        result = self.service.ingest((payload(),), as_of=self.cutoff)
        self.assertEqual(result.receipts[0].disposition, IngestionDisposition.REPLAY)
        self.assertEqual(result.total_documents, 1)

    def test_conflicting_replay_is_atomic(self):
        self.service.ingest((payload(),), as_of=self.cutoff)
        with self.assertRaises(ValueError):
            self.service.ingest((payload(document_id="doc-2"),
                                 payload(content="Alterado")), as_of=self.cutoff)
        self.assertEqual(len(self.service.snapshot(as_of=self.cutoff)), 1)

    def test_invalid_batch_is_atomic(self):
        with self.assertRaises(KeyError):
            self.service.ingest((payload(), payload(source_id="unknown")), as_of=self.cutoff)
        self.assertEqual(self.service.snapshot(as_of=self.cutoff), ())

    def test_duplicate_revision_rejected(self):
        with self.assertRaises(ValueError):
            self.service.ingest((payload(), payload()), as_of=self.cutoff)

    def test_future_document_rejected(self):
        with self.assertRaises(ValueError):
            self.service.ingest((payload(),), as_of=T)

    def test_revision_order_allowed(self):
        result = self.service.ingest((payload(revision=2, received_at=T + timedelta(minutes=2)),
                                      payload()), as_of=self.cutoff)
        self.assertEqual([doc.revision for doc in result.documents], [1, 2])

    def test_revision_time_conflict_rejected(self):
        with self.assertRaises(ValueError):
            self.service.ingest((payload(revision=2),
                                 payload(received_at=T + timedelta(minutes=2))),
                                as_of=self.cutoff)
        self.assertEqual(self.service.snapshot(as_of=self.cutoff), ())

    def test_time_cutoff_cannot_go_backwards(self):
        self.service.ingest((payload(),), as_of=self.cutoff)
        with self.assertRaises(ValueError):
            self.service.ingest((), as_of=T)

    def test_snapshot_respects_cutoff(self):
        self.service.ingest((payload(),), as_of=self.cutoff)
        self.assertEqual(self.service.snapshot(as_of=T), ())

    def test_naive_as_of_rejected(self):
        with self.assertRaises(ValueError):
            self.service.ingest((), as_of=T.replace(tzinfo=None))

    def test_receipt_immutable(self):
        result = self.service.ingest((payload(),), as_of=self.cutoff)
        with self.assertRaises(FrozenInstanceError):
            result.receipts[0].revision = 2

    def test_empty_batch(self):
        result = self.service.ingest((), as_of=self.cutoff)
        self.assertEqual(result.receipts, ())
        self.assertEqual(result.total_documents, 0)


if __name__ == "__main__":
    unittest.main()
