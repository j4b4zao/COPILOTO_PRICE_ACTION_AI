"""Offline event extraction and provenance through the A5 ingestion contract."""

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
import socket

import pytest

from political_market_intelligence.event_model import EventCategory, EventRecord
from political_market_intelligence.official_document_normalizer import (
    DocumentObservation, DocumentState,
)
from political_market_intelligence.official_event_extractor import (
    ExtractedOfficialEvent, OfficialEventCategory, OfficialEventExtractor,
)
from political_market_intelligence.official_ingestion_service import OfficialIngestionService
from political_market_intelligence.official_source_catalog import (
    OfficialSource, OfficialSourceCatalog, OfficialSourceKind,
)


PUBLISHED = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
RECEIVED = PUBLISHED + timedelta(minutes=1)
CUTOFF = RECEIVED + timedelta(minutes=1)
SELIC = "O Copom manteve a taxa Selic em 12,25% ao ano."
STATEMENTS = (
    ("O IBGE divulgou o IPCA de 0,25%.", OfficialEventCategory.ECONOMIC_INDICATOR),
    (SELIC, OfficialEventCategory.MONETARY_POLICY),
    ("O Tesouro Nacional divulgou o resultado primário com déficit de R$ 2 bilhões.",
     OfficialEventCategory.FISCAL_COMMUNICATION),
    ("O Governo Federal anunciou a redução do IPI.", OfficialEventCategory.ECONOMIC_MEASURE),
    ("A Secex publicou o boletim da balança comercial.", OfficialEventCategory.FOREIGN_TRADE),
    ("A CVM publicou a Resolução nº 123/2026.", OfficialEventCategory.REGULATORY_CHANGE),
)


def payload(**changes):
    return dict({
        "source_id": "candidate", "document_id": "doc-1", "revision": 1,
        "title": "Comunicado", "content": SELIC,
        "published_at": PUBLISHED, "received_at": RECEIVED,
    }, **changes)


@pytest.fixture
def stack():
    catalog = OfficialSourceCatalog((OfficialSource(
        source_id="candidate", institution="Instituição de teste", country_code="BR",
        kind=OfficialSourceKind.COMMUNICATION, candidate_url="https://example.org/",
        capabilities={EventCategory.CONFIRMED_FACT},
    ),))
    return OfficialIngestionService(catalog), OfficialEventExtractor(catalog)


def test_explicit_event_preserves_provenance(stack):
    ingestion, extractor = stack
    doc, = ingestion.ingest((payload(content=f"Introdução.\r\n  {SELIC}  "),), as_of=CUTOFF).documents
    event, = extractor.extract((doc,), as_of=RECEIVED.astimezone(timezone(timedelta(hours=-3))))
    assert event.category is OfficialEventCategory.MONETARY_POLICY
    assert (event.source_id, event.document_id, event.revision) == doc.key
    assert (event.published_at, event.available_at) == (PUBLISHED, RECEIVED)
    assert event.available_at.tzinfo is timezone.utc
    assert event.content_sha256 == doc.content_sha256
    assert event.description == doc.content[event.content_start:event.content_end] == SELIC
    assert event.state is DocumentState.UNVERIFIED


@pytest.mark.parametrize("content", [
    "Texto local sem fato identificável.",
    "Selic\nIPCA\nComércio exterior",
    "O Copom não manteve a taxa Selic em 12,25% ao ano.",
    "O Copom manteve a taxa Selic em 12,25% ao ano?",
    "Se o Copom manteve a taxa Selic em 12,25% ao ano.",
    '"O Copom manteve a taxa Selic em 12,25% ao ano."',
    "O Copom poderá manter a taxa Selic em 12,25% ao ano.",
])
def test_ignores_unidentifiable_or_ambiguous_content(stack, content):
    _, extractor = stack
    doc = DocumentObservation(**payload(content=content, title=SELIC))
    assert extractor.extract((doc,), as_of=CUTOFF) == ()


def test_multiple_categories_and_statements(stack):
    _, extractor = stack
    doc = DocumentObservation(**payload(content="\n".join(text for text, _ in STATEMENTS)))
    events = extractor.extract((doc,), as_of=CUTOFF)
    assert [(e.description, e.category) for e in events] == list(STATEMENTS)
    assert len({e.event_id for e in events}) == len(STATEMENTS)


def test_deterministic_and_idempotent_replay(stack):
    ingestion, extractor = stack
    inputs = (payload(document_id="doc-2"), payload())
    first = ingestion.ingest(inputs, as_of=RECEIVED)
    replay = ingestion.ingest(tuple(reversed(inputs)), as_of=CUTOFF)
    expected = extractor.extract(first.documents, as_of=RECEIVED)
    assert len(expected) == 2
    assert extractor.extract(list(reversed(replay.documents)), as_of=CUTOFF) == expected
    assert extractor.extract(first.documents + replay.documents, as_of=CUTOFF) == expected


def test_revision_history_and_cutoff(stack):
    ingestion, extractor = stack
    first = ingestion.ingest((payload(),), as_of=RECEIVED)
    second = ingestion.ingest((payload(revision=2, received_at=CUTOFF),), as_of=CUTOFF)
    events = extractor.extract(second.documents, as_of=CUTOFF)
    assert [event.revision for event in events] == [1, 2]
    assert events[0].event_id != events[1].event_id
    assert extractor.extract(ingestion.snapshot(as_of=RECEIVED), as_of=RECEIVED) == events[:1]
    assert extractor.extract(first.documents, as_of=RECEIVED) == events[:1]
    with pytest.raises(ValueError, match="higher revision"):
        extractor.extract((replace(first.documents[0], received_at=CUTOFF),
                           replace(second.documents[1], received_at=RECEIVED)), as_of=CUTOFF)


def test_conflicting_identity_rejected(stack):
    _, extractor = stack
    doc = DocumentObservation(**payload())
    with pytest.raises(ValueError, match="conflicting document identity"):
        extractor.extract((doc, replace(doc, title="Outro comunicado")), as_of=CUTOFF)


def test_rejects_malformed_and_invalid_clock(stack):
    _, extractor = stack
    with pytest.raises(TypeError, match="normalized"):
        extractor.extract((payload(),), as_of=CUTOFF)
    with pytest.raises(ValueError, match="timezone-aware"):
        extractor.extract((), as_of=CUTOFF.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        DocumentObservation(**payload(received_at=RECEIVED.replace(tzinfo=None)))


@pytest.mark.parametrize("cutoff", [PUBLISHED - timedelta(seconds=1), PUBLISHED])
def test_rejects_unavailable_document(stack, cutoff):
    _, extractor = stack
    with pytest.raises(ValueError, match="cutoff"):
        extractor.extract((DocumentObservation(**payload()),), as_of=cutoff)


def test_rejects_missing_or_inconsistent_provenance(stack):
    _, extractor = stack
    with pytest.raises(KeyError, match="unknown"):
        extractor.extract((DocumentObservation(**payload(source_id="unknown")),), as_of=CUTOFF)
    doc = DocumentObservation(**payload())
    object.__setattr__(doc, "content_sha256", "")
    with pytest.raises(ValueError, match="provenance"):
        extractor.extract((doc,), as_of=CUTOFF)


def test_immutable_inputs_and_observational_output(stack):
    _, extractor = stack
    doc = DocumentObservation(**payload())
    original = replace(doc)
    batch = [doc]
    event, = extractor.extract(batch, as_of=CUTOFF)
    assert batch == [original] and batch[0] is doc
    with pytest.raises(FrozenInstanceError):
        doc.content = "alterado"
    with pytest.raises(FrozenInstanceError):
        event.description = "alterada"
    assert type(event) is ExtractedOfficialEvent and not isinstance(event, EventRecord)
    assert {field.name for field in fields(event)} == {
        "event_id", "source_id", "document_id", "revision", "category", "description",
        "published_at", "available_at", "content_sha256", "content_start", "content_end", "state",
    }


def test_ingestion_and_extraction_do_not_access_network(stack, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("network access")

    monkeypatch.setattr(socket, "socket", unexpected)
    monkeypatch.setattr(socket, "getaddrinfo", unexpected)
    monkeypatch.setattr(socket, "create_connection", unexpected)
    ingestion, extractor = stack
    docs = ingestion.ingest((payload(),), as_of=CUTOFF).documents
    assert len(extractor.extract(docs, as_of=CUTOFF)) == 1
