"""PMI-RC2-A4: offline document normalization contract tests."""
import unittest
from datetime import datetime, timedelta, timezone
from dataclasses import FrozenInstanceError

from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_source_catalog import OfficialSource, OfficialSourceCatalog, OfficialSourceKind
from political_market_intelligence.official_document_normalizer import OfficialDocumentNormalizer, DocumentObservation

T = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)


def payload(**changes):
    item = dict(source_id="test-source", document_id="doc-1", revision=1,
                title="Comunicado", content="Texto local", published_at=T,
                received_at=T + timedelta(minutes=2))
    item.update(changes)
    return item


class NormalizerTests(unittest.TestCase):
    def setUp(self):
        source = OfficialSource(source_id="test-source", institution="Instituicao de teste",
                                country_code="BR", kind=OfficialSourceKind.COMMUNICATION,
                                candidate_url="https://example.org/", capabilities=frozenset({EventCategory.CONFIRMED_FACT}))
        self.normalizer = OfficialDocumentNormalizer(OfficialSourceCatalog((source,)))
        self.cutoff = T + timedelta(minutes=3)

    def test_normalizes_unverified(self):
        doc = self.normalizer.normalize(payload(), as_of=self.cutoff)
        self.assertEqual(doc.state.value, "UNVERIFIED")
        self.assertEqual(len(doc.content_sha256), 64)

    def test_no_lookahead(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize(payload(), as_of=T)

    def test_unknown_source(self):
        with self.assertRaises(KeyError):
            self.normalizer.normalize(payload(source_id="unknown"), as_of=self.cutoff)

    def test_extra_field_rejected(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize(payload(verified_at=T), as_of=self.cutoff)

    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize(payload(published_at=T.replace(tzinfo=None)), as_of=self.cutoff)

    def test_reversed_clocks_rejected(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize(payload(received_at=T - timedelta(seconds=1)), as_of=self.cutoff)

    def test_invalid_revision_rejected(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize(payload(revision=True), as_of=self.cutoff)

    def test_hash_tamper_rejected(self):
        with self.assertRaises(ValueError):
            DocumentObservation(**payload(), content_sha256="bad")

    def test_immutable(self):
        doc = self.normalizer.normalize(payload(), as_of=self.cutoff)
        with self.assertRaises(FrozenInstanceError):
            doc.content = "changed"

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize_many((payload(), payload()), as_of=self.cutoff)

    def test_sorted_revisions(self):
        docs = self.normalizer.normalize_many((payload(revision=2), payload()), as_of=self.cutoff)
        self.assertEqual([d.revision for d in docs], [1, 2])

    def test_utc_conversion(self):
        other = timezone(timedelta(hours=-3))
        doc = self.normalizer.normalize(payload(published_at=T.astimezone(other)), as_of=self.cutoff)
        self.assertEqual(doc.published_at, T)

    def test_reject_future_cutoff_naive(self):
        with self.assertRaises(ValueError):
            self.normalizer.normalize(payload(), as_of=self.cutoff.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
