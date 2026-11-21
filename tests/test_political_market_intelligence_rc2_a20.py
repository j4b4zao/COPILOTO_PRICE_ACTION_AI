"""Bounded paragraph continuity and unchanged evidence and security gates."""

from dataclasses import replace
from datetime import timedelta

import pytest

from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


RATE_LEAD = "O Copom fixou a Selic em"
RATE_TAIL = "10,25% ao ano."
RATE = RATE_LEAD + "\r\n\r\n" + RATE_TAIL
REGULATION = "A CVM publicou a Resolução nº 716/2025."


@pytest.mark.parametrize(("content", "category"), [
    (RATE, "MONETARY_POLICY"),
    ("O Copom decidiu\n\nmanter a Selic em 10,25%.", "MONETARY_POLICY"),
    ("O Banco Central reduziu a Selic para 10,\n\n25%.", "MONETARY_POLICY"),
    ("O IBGE divulgou o PIB de\n\n2,5%.", "ECONOMIC_INDICATOR"),
    ("O IBGE informou que o IPCA foi\n\nde 0,51%.", "ECONOMIC_INDICATOR"),
    ("O IBGE divulgou o IPCA de 0,\r\n\r\n51%.", "ECONOMIC_INDICATOR"),
    ("O Tesouro Nacional divulgou o resultado primário\r\n \t\r\n"
     "com superávit de R$ 8 milhões.", "FISCAL_COMMUNICATION"),
    ("O Tesouro Nacional divulgou o resultado primário com superávit de R$ 8\n\n"
     "milhões.", "FISCAL_COMMUNICATION"),
    ("A CVM alte-\n\nrou a Resolução nº 716/2025.", "REGULATORY_CHANGE"),
    ("A CVM revogou\n\na Instrução nº 716/2025.", "REGULATORY_CHANGE"),
    ("A CVM publicou a Resolução nº\n\n716/2025.", "REGULATORY_CHANGE"),
    ("O MDIC divulgou o boletim da\n\nbalança comercial.", "FOREIGN_TRADE"),
])
def test_controlled_continuation_leaves_source_evidence_unchanged(catalog, content, category):
    text = "Nota 📄.\n\n  " + content + "\n\n" + REGULATION
    doc = document(text)
    extractor = OfficialEventExtractor(catalog)
    events = extractor.extract((doc,), as_of=CUT)
    assert len(events) == 2
    event = events[0]
    assert event.category.value == category
    assert event.description == text[event.content_start:event.content_end] == content
    assert event.content_start == text.index(content)
    assert event.content_sha256 == doc.content_sha256
    assert event.state is DocumentState.UNVERIFIED
    assert (event.source_id, event.document_id, event.revision) == doc.key
    assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
    assert events[1].description == REGULATION
    assert extractor.extract((doc, doc), as_of=CUT) == events


@pytest.mark.parametrize("text", [
    RATE_LEAD + "\n\n\n" + RATE_TAIL,
    RATE_LEAD + ".\n\n" + RATE_TAIL,
    RATE_LEAD + "\n\n## Taxas de referência\n" + RATE_TAIL,
    RATE_LEAD + "\n\n## Decisões oficiais\n" + RATE_TAIL,
    RATE_LEAD + "\n\n" + RATE_TAIL.rstrip(".") + "?",
    RATE_LEAD + "\n\n" + RATE_TAIL.rstrip(".") + " se o cenário se confirmar.",
    RATE_LEAD + "\n\n" + RATE_TAIL.rstrip(".") + " em 2027.",
    "O Copom não fixou a Selic em\n\n" + RATE_TAIL,
    "Versão de trabalho:\n" + RATE,
    "Projeção para o próximo trimestre:\n\n" + RATE,
    "Exercício com dados fictícios.\n\n" + RATE,
    "Se a condição se cumprir:\n\n" + RATE,
    "A afirmação abaixo é uma alegação de terceiros.\n\n" + RATE,
    RATE + "\n\nA nota desmente integralmente a frase anterior.",
])
def test_incompatible_or_nonfactual_fragments_are_not_joined(catalog, text):
    assert OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT) == ()


def test_distinct_statements_and_factual_sections_survive(catalog):
    text = "Hipótese:\n" + RATE + "\n\n## Decisões oficiais\n" + RATE_LEAD + "\n\n" + REGULATION
    event, = OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT)
    assert event.description == REGULATION
    assert event.content_start == text.index(REGULATION)


def test_continuation_respects_revision_cutoff_and_strict_provenance(catalog):
    doc = document(RATE, received_at=CUT)
    previous = replace(doc, received_at=CUT - timedelta(seconds=1))
    revision = replace(doc, revision=2)
    extractor = OfficialEventExtractor(catalog)
    assert [event.revision for event in extractor.extract((revision, previous), as_of=CUT)] == [1, 2]
    with pytest.raises(ValueError, match="cutoff"):
        extractor.extract((previous, revision), as_of=CUT - timedelta(microseconds=1))
    for field, value in (("state", "UNVERIFIED"), ("content_sha256", "0" * 64)):
        altered = replace(doc)
        object.__setattr__(altered, field, value)
        with pytest.raises(ValueError, match="provenance"):
            extractor.extract((altered,), as_of=CUT)
