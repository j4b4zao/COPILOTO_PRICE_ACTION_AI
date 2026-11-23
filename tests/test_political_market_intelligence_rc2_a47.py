"""Literal decimal fragments and the boundaries that qualify them."""

from datetime import timedelta
from hashlib import sha256
import re
from unicodedata import normalize

import pytest

from audit.pmi_rc2_a21 import CASES, CATEGORIES, X
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


@pytest.fixture(params=["multifragment-decimal", "decimal-with-two-empty-lines"])
def fragmented_decimal(request):
    return next((text, CATEGORIES[code]) for label, text, code, _ in CASES if label == request.param)


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_decimal_fragments_preserve_literal_evidence(catalog, fragmented_decimal, newline):
    text, category = fragmented_decimal
    text = text.replace("\n", newline)
    prefix = "Nota 🧾." + newline * 2 + "  "
    first = document(prefix + text + newline * 2 + X)
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
def test_qualified_decimal_does_not_suppress_the_next_fact(
    catalog, fragmented_decimal, prefix, factual_heading,
):
    text, _ = fragmented_decimal
    engine = OfficialEventExtractor(catalog)
    qualified = prefix + "\n\n" + text
    assert engine.extract((document(qualified),), as_of=CUT) == ()
    content = qualified + "\n\n" + factual_heading + X
    event, = engine.extract((document(content),), as_of=CUT)
    assert content[event.content_start:event.content_end] == event.description == X


@pytest.mark.parametrize(("interruption", "expected"), [
    pytest.param("## Fatos documentados\n\n", [X], id="heading"),
    pytest.param("| Série | Valor |\n| Outra | 75% |\n\n", [X], id="table"),
    pytest.param("75\n\n", [X], id="independent-digits"),
    pytest.param("75% é a taxa de outra série.\n\n", [X], id="independent-percent"),
    pytest.param(X + "\n\n", [X, X], id="intervening-event"),
    pytest.param("\n", [X], id="extra-empty-line"),
])
def test_decimal_does_not_cross_an_interruption(catalog, fragmented_decimal, interruption, expected):
    text, _ = fragmented_decimal
    lead, gap, tail = re.split(r"(?<=,)(\n+)(?=[0-9])", text, maxsplit=1)
    content = lead + gap + interruption + tail + "\n\n" + X
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert [event.description for event in events] == expected
    assert all(content[event.content_start:event.content_end] == X for event in events)


def test_retraction_removes_only_the_decimal_fact(catalog, fragmented_decimal):
    text, _ = fragmented_decimal
    content = text + "\n\nRetratação: a informação acima foi desmentida.\n\n" + X
    event, = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert event.description == X
