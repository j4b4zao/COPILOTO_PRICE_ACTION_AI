"""Bounded continuation across extended gaps in two official statements."""

from datetime import timedelta
from hashlib import sha256
import re
from unicodedata import normalize

import pytest

from audit.pmi_rc2_a21 import CASES, CATEGORIES, X
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


@pytest.fixture(params=["three-empty-lines", "crlf-two-empty-lines"])
def extended_gap_case(request):
    return next((text, CATEGORIES[code]) for label, text, code, _ in CASES if label == request.param)


def test_extended_gap_preserves_provenance_and_replay(catalog, extended_gap_case):
    text, category = extended_gap_case
    prefix = "Nota 🧾.\r\n\r\n  "
    content = prefix + text + "\r\n\r\n" + X
    first = document(content)
    second = document(text, revision=2, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))

    events = engine.extract((first, second), as_of=CUT)
    assert [(event.revision, event.category.value, event.description) for event in events] == [
        (1, category, text), (1, "FOREIGN_TRADE", X), (2, category, text),
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
def test_qualified_extended_gap_keeps_the_next_fact(catalog, extended_gap_case, prefix, factual_heading):
    text, _ = extended_gap_case
    engine = OfficialEventExtractor(catalog)
    qualified = prefix + "\n\n" + text
    assert engine.extract((document(qualified),), as_of=CUT) == ()
    content = qualified + "\n\n" + factual_heading + X
    event, = engine.extract((document(content),), as_of=CUT)
    assert content[event.content_start:event.content_end] == event.description == X


@pytest.mark.parametrize("interruption", [
    pytest.param("## Fatos documentados\n\n", id="factual-heading"),
    pytest.param("## Tabela de referência\nSérie | Valor\nOutra | 7%\n\n", id="table"),
    pytest.param("7,25% é a taxa de outra série.\n\n", id="independent-percent"),
    pytest.param(X + "\n\n", id="intervening-event"),
    pytest.param("\r\n", id="extra-empty-line"),
])
def test_interruption_prevents_continuation_across_the_gap(catalog, extended_gap_case, interruption):
    text, _ = extended_gap_case
    lead, gap, tail = re.split(r"(\r?\n(?:[ \t]*\r?\n)+)", text, maxsplit=1)
    content = lead + gap + interruption + tail + "\n\n" + X
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    expected = [X, X] if interruption.startswith(X) else [X]
    assert [event.description for event in events] == expected
    assert all(content[event.content_start:event.content_end] == X for event in events)


def test_backward_retraction_removes_only_the_extended_gap_fact(catalog, extended_gap_case):
    text, _ = extended_gap_case
    content = text + "\n\nRetratação: a informação acima foi desmentida.\n\n" + X
    event, = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert event.description == X


@pytest.mark.parametrize("gap", ["\n \n\t\n", "\r\n\r\n\r\n"])
def test_indicator_extended_gap_requires_crlf_with_padding(catalog, gap):
    content = "O IBGE divulgou o IBC-Br de" + gap + "0,8%.\n\n" + X
    event, = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert event.description == X
