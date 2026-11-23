"""Bounded continuation of four statements with fragmented subjects."""

from hashlib import sha256
from unicodedata import normalize

import pytest

from audit.pmi_rc2_a21 import CASES, CATEGORIES, X
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


CASES_A45 = [
    pytest.param(text, CATEGORIES[category], id=label)
    for label, text, category, _ in CASES
    if label in {"fiscal-four", "measure-four", "monetary-three", "indicator-three"}
]


@pytest.mark.parametrize(("text", "category"), CASES_A45)
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_recovers_fragmented_subject_with_literal_evidence(catalog, text, category, newline):
    prefix = "Nota 🧾." + newline * 2 + "  "
    literal = text.replace("\n", newline)
    content = prefix + literal + newline * 2 + X
    doc = document(content)
    engine = OfficialEventExtractor(catalog)
    events = engine.extract((doc,), as_of=CUT)
    assert [(event.description, event.category.value) for event in events] == [
        (literal, category), (X, "FOREIGN_TRADE"),
    ]
    event = events[0]
    assert (event.content_start, event.content_end) == (len(prefix), len(prefix) + len(literal))
    for event in events:
        assert content[event.content_start:event.content_end] == event.description
        assert event.content_sha256 == doc.content_sha256 == sha256(content.encode("utf-8")).hexdigest()
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
    assert engine.extract((doc, doc), as_of=CUT) == events


@pytest.mark.parametrize(("text", "category"), CASES_A45)
@pytest.mark.parametrize(("prefix", "factual_heading"), [
    pytest.param("É falso que o fato abaixo tenha ocorrido.", "", id="negation"),
    pytest.param("Se houver aprovação:", "", id="condition"),
    pytest.param("Hipótese:", "Fatos documentados\n\n", id="hypothesis"),
    pytest.param("A afirmação abaixo é uma alegação de terceiros.", "", id="third-party"),
    pytest.param("Informação desmentida sobre o fato a seguir:", "", id="disavowal"),
    pytest.param("Retratação sobre o fato abaixo:", "", id="forward-retraction"),
    pytest.param("Se houver aprovação \t:", "", id="space-before-colon"),
    pytest.param("É falso que o fato abaixo tenha ocorrido…", "", id="unicode-ellipsis"),
    pytest.param(normalize("NFD", "É falso que o fato abaixo tenha ocorrido."), "", id="nfd"),
])
def test_qualified_fragments_do_not_suppress_the_next_fact(
    catalog, text, category, prefix, factual_heading,
):
    engine = OfficialEventExtractor(catalog)
    qualified = prefix + "\n\n" + text
    assert engine.extract((document(qualified),), as_of=CUT) == ()
    content = qualified + "\n\n" + factual_heading + X
    event, = engine.extract((document(content),), as_of=CUT)
    assert event.description == X
    assert content[event.content_start:event.content_end] == X


@pytest.mark.parametrize(("text", "category"), CASES_A45)
@pytest.mark.parametrize("interruption", [
    pytest.param("\n\n## Tabela de referência\n\nSérie | Valor\nOutra | 7%", id="adjacent-table"),
    pytest.param("\n\n7,25% é a taxa de outra série.", id="independent-value"),
    pytest.param(".", id="sentence-end"),
    pytest.param("\n", id="extra-empty-line"),
])
def test_interrupted_fragments_do_not_absorb_independent_content(catalog, text, category, interruption):
    lead, tail = text.rsplit("\n\n", 1)
    content = lead + interruption + "\n\n" + tail + "\n\n" + X
    event, = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert event.description == X


@pytest.mark.parametrize(("text", "category"), CASES_A45)
def test_retraction_removes_only_the_fragmented_fact(catalog, text, category):
    content = text + "\n\nRetratação: a informação acima foi desmentida.\n\n" + X
    event, = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert event.description == X
