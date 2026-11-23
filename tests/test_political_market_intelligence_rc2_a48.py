"""Literal evidence for a CVM instruction number and year split by layout."""

from datetime import timedelta
from hashlib import sha256
from unicodedata import normalize

import pytest

from audit.pmi_rc2_a21 import CASES, X
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


REFERENCE = next(text for label, text, _, _ in CASES if label == "regulatory-reference")


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_split_instruction_keeps_literal_evidence_and_replay(catalog, newline):
    text = REFERENCE.replace("\n", newline)
    prefix = "Nota 🧾." + newline * 2 + "  "
    first = document(prefix + text + newline * 2 + X)
    second = document(text, revision=2, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))

    events = engine.extract((first, second), as_of=CUT)
    assert [(event.revision, event.category.value, event.description) for event in events] == [
        (1, "REGULATORY_CHANGE", text), (1, "FOREIGN_TRADE", X), (2, "REGULATORY_CHANGE", text),
    ]
    assert (events[0].content_start, events[0].content_end) == (len(prefix), len(prefix) + len(text))
    for event, doc in zip(events, (first, first, second), strict=True):
        assert doc.content[event.content_start:event.content_end] == event.description
        assert event.content_sha256 == doc.content_sha256 == sha256(doc.content.encode("utf-8")).hexdigest()
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
    assert engine.extract((second, first, first), as_of=CUT) == events


@pytest.mark.parametrize(("prefix", "factual_heading"), [
    pytest.param("É falso que o fato abaixo tenha ocorrido.", "", id="negation"),
    pytest.param("Se houver aprovação:", "", id="condition"),
    pytest.param("Hipótese:", "Fatos documentados\n\n", id="hypothesis"),
    pytest.param("A afirmação abaixo é uma alegação de terceiros.", "", id="third-party"),
    pytest.param("Retratação sobre o fato abaixo:", "", id="forward-retraction"),
    pytest.param("Se houver aprovação \t:", "", id="space-before-colon"),
    pytest.param("É falso que o fato abaixo tenha ocorrido…", "", id="unicode-ellipsis"),
    pytest.param(normalize("NFD", "É falso que o fato abaixo tenha ocorrido."), "", id="nfd"),
])
def test_qualified_instruction_keeps_later_independent_event(catalog, prefix, factual_heading):
    engine = OfficialEventExtractor(catalog)
    qualified = prefix + "\n\n" + REFERENCE
    assert engine.extract((document(qualified),), as_of=CUT) == ()
    content = qualified + "\n\n" + factual_heading + X
    event, = engine.extract((document(content),), as_of=CUT)
    assert content[event.content_start:event.content_end] == event.description == X


@pytest.mark.parametrize("text", [
    pytest.param(REFERENCE.replace("54/", "Resolução nº 54/"), id="number-of-another-act"),
    pytest.param(REFERENCE.replace("2021.", "2021 é o ano da Resolução nº 90."), id="year-of-another-act"),
    pytest.param(REFERENCE.replace("2021.", "## Fatos documentados\n\n2021."), id="heading"),
    pytest.param(REFERENCE.replace("2021.", "| Ato | Ano |\n| Outro | 2021 |"), id="table"),
    pytest.param(REFERENCE.removesuffix("\n\n2021."), id="missing-year"),
    pytest.param(REFERENCE.replace("2021.", "202."), id="incomplete-year"),
    pytest.param(REFERENCE.replace("54/", "/"), id="missing-number"),
    pytest.param(REFERENCE.replace("/\n\n", "/\n\n\n"), id="extra-empty-line"),
    pytest.param(REFERENCE.replace("editou", "não editou"), id="negated-action"),
    pytest.param(REFERENCE + "\n\nRetratação: a informação acima foi desmentida.", id="retraction"),
])
def test_invalid_instruction_reference_leaves_next_fact_intact(catalog, text):
    engine = OfficialEventExtractor(catalog)
    assert engine.extract((document(text),), as_of=CUT) == ()
    content = text + "\n\n" + X
    event, = engine.extract((document(content),), as_of=CUT)
    assert content[event.content_start:event.content_end] == event.description == X


def test_does_not_take_year_past_an_intervening_event(catalog):
    content = REFERENCE.replace("2021.", X + "\n\n2021.") + "\n\n" + X
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert [event.description for event in events] == [X, X]
    assert all(content[event.content_start:event.content_end] == X for event in events)
