"""PMI-RC2-A3: fail-closed, offline metadata catalog tests."""

from dataclasses import FrozenInstanceError
import unittest

from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_source_catalog import (
    OfficialSource, OfficialSourceCatalog, OfficialSourceKind,
)
from political_market_intelligence.source_registry import SourceStatus


def source(**overrides):
    values = dict(
        source_id="br-central-bank-candidate",
        institution="Banco Central",
        country_code="BR",
        kind=OfficialSourceKind.COMMUNICATION,
        candidate_url="https://www.example.org/publications",
        capabilities=frozenset({EventCategory.CONFIRMED_FACT}),
    )
    values.update(overrides)
    return OfficialSource(**values)


class OfficialSourceCatalogTests(unittest.TestCase):
    def test_defaults_fail_closed(self):
        entry = source()
        self.assertIs(entry.status, SourceStatus.UNVERIFIED)
        self.assertIs(entry.collection_enabled, False)

    def test_metadata_only_no_network(self):
        catalog = OfficialSourceCatalog((source(),))
        self.assertEqual(catalog.get("br-central-bank-candidate"), source())
        self.assertEqual(len(catalog.all()), 1)

    def test_deterministic_order(self):
        a = source(source_id="a")
        z = source(source_id="z")
        self.assertEqual(OfficialSourceCatalog((z, a)).all(), (a, z))

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            OfficialSourceCatalog((source(), source()))

    def test_unknown_rejected(self):
        with self.assertRaises(KeyError):
            OfficialSourceCatalog().get("unknown")

    def test_invalid_source_fields(self):
        for override in (
            {"source_id": " "}, {"institution": " Banco Central"},
            {"country_code": "br"}, {"country_code": "BRA"},
            {"kind": "SPEECH"}, {"capabilities": frozenset()},
            {"capabilities": {"CONFIRMED_FACT"}},
        ):
            with self.subTest(override=override), self.assertRaises(ValueError):
                source(**override)

    def test_unsafe_urls_rejected(self):
        for url in (
            "http://www.example.org", "https://localhost/x",
            "https://127.0.0.1/x", "https://user:secret@example.org/x",
            "https://www.example.org:8443/x", "https://www.example.org/x?token=abc",
            "https://www.example.org/x#fragment", "https://www.example.org/x\n",
            "file:///etc/passwd", "https://example.org@localhost/x",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                source(candidate_url=url)

    def test_collection_not_authorized(self):
        with self.assertRaises(ValueError):
            source(collection_enabled=True)

    def test_verified_not_authorized(self):
        with self.assertRaises(ValueError):
            source(status=SourceStatus.AVAILABLE)

    def test_frozen(self):
        entry = source()
        with self.assertRaises(FrozenInstanceError):
            entry.institution = "Changed"

    def test_wrong_catalog_input(self):
        with self.assertRaises(TypeError):
            OfficialSourceCatalog((object(),))


if __name__ == "__main__":
    unittest.main()
