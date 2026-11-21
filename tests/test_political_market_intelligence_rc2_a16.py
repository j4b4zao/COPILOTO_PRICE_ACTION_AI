"""Semantic qualifiers and strict document validation for A16."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from enum import Enum

import pytest

from political_market_intelligence.event_model import EventCategory
from political_market_intelligence.official_document_normalizer import DocumentObservation, DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from political_market_intelligence.official_ingestion_service import OfficialIngestionService
from political_market_intelligence.official_source_catalog import OfficialSource, OfficialSourceCatalog, OfficialSourceKind


AT = datetime(2026, 11, 21, 15, tzinfo=timezone.utc)
LATER = AT + timedelta(minutes=1)
INDICATOR = "O IBGE divulgou o IPCA de 0,31%."
DECISION = "O Copom reduziu a Selic para 10,75%."
RETRACTION = "Retratação: a informação acima foi desmentida."


def payload(content=INDICATOR, **overrides):
    return dict(
        source_id="synthetic", document_id="a16", revision=1, title="Local",
        content=content, published_at=AT, received_at=AT,
    ) | overrides


@pytest.fixture
def catalog():
    return OfficialSourceCatalog((OfficialSource(
        source_id="synthetic", institution="Synthetic", country_code="BR",
        candidate_url="https://example.org", kind=OfficialSourceKind.COMMUNICATION,
        capabilities={EventCategory.CONFIRMED_FACT},
    ),))


@pytest.mark.parametrize("qualifier", [
    RETRACTION,
    "O comunicado desmente a afirmação anterior.",
    "A frase anterior descreve uma decisão prevista para o futuro.",
    "O órgão nega que essa divulgação tenha ocorrido.",
])
def test_backward_qualifier_preserves_independent_events(catalog, qualifier):
    content = f"{DECISION}\r\n\r\n{INDICATOR}\r\n{qualifier}\r\n\r\n{DECISION}"
    doc = DocumentObservation(**payload(content))
    extractor = OfficialEventExtractor(catalog)
    events = extractor.extract((doc,), as_of=AT)
    assert [e.description for e in events] == [DECISION, DECISION]
    assert [e.content_start for e in events] == [0, content.rindex(DECISION)]
    for event in events:
        assert content[event.content_start:event.content_end] == event.description
        assert event.content_sha256 == doc.content_sha256
        assert event.state is DocumentState.UNVERIFIED
    assert extractor.extract((doc, doc), as_of=AT) == events
    assert OfficialEventExtractor(catalog).extract((doc,), as_of=AT) == events


@pytest.mark.parametrize("qualifier", [
    "Para fins ilustrativos, adota-se a premissa abaixo.",
    "Texto sob revisão para divulgação na próxima semana.",
    "Estimativa para o próximo mês:",
    "Não procede a afirmação abaixo:",
    "Caso a medida seja concedida:",
    "Se a condição se cumprir, considere o texto abaixo.",
])
def test_forward_context_ends_at_independent_factual_heading(catalog, qualifier):
    content = f"{qualifier}\n\n{INDICATOR}\n\n## Decisões oficiais\n{DECISION}"
    doc = DocumentObservation(**payload(content))
    event, = OfficialEventExtractor(catalog).extract((doc,), as_of=AT)
    assert event.description == DECISION
    assert event.content_start == content.index(DECISION)


def test_non_retracting_erratum_keeps_statement(catalog):
    content = INDICATOR + "\nCorreção: o boletim mudou de título. O dado permanece válido."
    event, = OfficialEventExtractor(catalog).extract((DocumentObservation(**payload(content)),), as_of=AT)
    assert event.description == INDICATOR


def test_later_revision_cannot_retract_past_snapshot(catalog):
    service = OfficialIngestionService(catalog)
    extractor = OfficialEventExtractor(catalog)
    service.ingest((payload(),), as_of=AT)
    initial = extractor.extract(service.snapshot(as_of=AT), as_of=AT)
    service.ingest((payload(INDICATOR + "\n" + RETRACTION,
                            revision=2, published_at=LATER, received_at=LATER),), as_of=LATER)
    history = service.snapshot(as_of=LATER)
    assert [doc.revision for doc in history] == [1, 2]
    assert len(initial) == 1 and initial[0].available_at == AT
    assert extractor.extract(service.snapshot(as_of=AT), as_of=AT) == initial
    assert extractor.extract(history, as_of=LATER) == initial
    with pytest.raises(ValueError, match="cutoff"):
        extractor.extract(history, as_of=AT)


class OtherState(str, Enum):
    UNVERIFIED = "UNVERIFIED"


@pytest.mark.parametrize("invalid", ["UNVERIFIED", OtherState.UNVERIFIED, None, 1, True, object()])
def test_rejects_tampered_state(catalog, invalid):
    doc = DocumentObservation(**payload())
    object.__setattr__(doc, "state", invalid)
    with pytest.raises(ValueError, match="provenance.*state"):
        OfficialEventExtractor(catalog).extract((doc,), as_of=AT)


def test_rejects_tampered_content_digest(catalog):
    doc = replace(DocumentObservation(**payload()))
    object.__setattr__(doc, "content_sha256", "0" * 64)
    with pytest.raises(ValueError, match="provenance"):
        OfficialEventExtractor(catalog).extract((doc,), as_of=AT)
