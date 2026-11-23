"""Explicit three-fragment trade and CVM instruction continuity."""

from datetime import timedelta
from hashlib import sha256
from unicodedata import normalize

import pytest

from audit.pmi_rc2_a21 import CASES, F
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


TRADE = next(text for label, text, _, _ in CASES if label == "trade-three")
REGULATION = next(text for label, text, _, _ in CASES if label == "regulatory-three")


@pytest.mark.parametrize(("text", "category"), [
    pytest.param(TRADE, "FOREIGN_TRADE", id="trade-three"),
    pytest.param(REGULATION, "REGULATORY_CHANGE", id="regulatory-three"),
])
def test_explicit_complement_preserves_literal_evidence(catalog, text, category):
    prefix = "Nota 🧾 sobre a edição.\r\n\r\n  "
    content = prefix + text
    doc = document(content)
    engine = OfficialEventExtractor(catalog)
    event, = events = engine.extract((doc,), as_of=CUT)
    assert event.category.value == category
    assert (event.content_start, event.content_end) == (len(prefix), len(content))
    assert event.description == content[event.content_start:event.content_end] == text
    assert event.content_sha256 == doc.content_sha256 == sha256(content.encode("utf-8")).hexdigest()
    assert (event.source_id, event.document_id, event.revision) == doc.key
    assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
    assert event.state is DocumentState.UNVERIFIED
    assert engine.extract((doc, doc), as_of=CUT) == events


@pytest.mark.parametrize("text", [
    pytest.param(TRADE.replace("Secex", "CVM"), id="incompatible-trade-actor"),
    pytest.param(REGULATION.replace("CVM", "Banco Central"), id="incompatible-regulatory-actor"),
    pytest.param(TRADE.replace("balança", "atividade"), id="different-object"),
    pytest.param(TRADE.replace("comercial.", "Comercial"), id="standalone-title"),
    pytest.param("comercial.", id="isolated-adjective"),
    pytest.param(TRADE.replace("comercial.", "## Comércio\n\ncomercial."), id="heading"),
    pytest.param(REGULATION.replace("54/2021.", "## Resultados oficiais\n54/2021."), id="section-change"),
    pytest.param("A afirmação abaixo é uma alegação de terceiros.\n\n" + TRADE, id="third-party-trade"),
    pytest.param("“" + REGULATION + "” — declarou a associação.", id="third-party-quotation"),
    pytest.param(REGULATION.replace("editou", "não editou"), id="negation"),
    pytest.param("Hipótese:\n" + REGULATION, id="hypothesis"),
    pytest.param("Minuta:\n" + REGULATION, id="draft"),
    pytest.param(REGULATION.replace("54/2021.", "54/2021 se a condição se cumprir."), id="future-condition"),
    pytest.param(REGULATION + "\n\nRetratação: a informação acima foi desmentida.", id="retraction"),
    pytest.param(REGULATION.replace("54/2021", "54"), id="incomplete-reference"),
    pytest.param(REGULATION.replace("54/2021", "54/\n\n2021"), id="split-reference"),
    pytest.param(REGULATION.replace("54/2021.", "Resolução nº 54/2021."), id="number-of-another-act"),
])
def test_invalid_continuation_is_not_emitted(catalog, text):
    assert OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT) == ()


@pytest.mark.parametrize("prefix", [
    pytest.param("Se houver aprovação:", id="a40-condition"),
    pytest.param("É falso que o fato abaixo tenha ocorrido.", id="a40-negation"),
    pytest.param("Se houver aprovação :", id="a42-space"),
    pytest.param("É falso que o fato abaixo tenha ocorrido…", id="a42-ellipsis"),
    pytest.param(normalize("NFD", "É falso que o fato abaixo tenha ocorrido."), id="a42-nfd"),
    pytest.param("Se houver aprovação\t :", id="tab-before-colon"),
    pytest.param("É falso que o fato abaixo tenha ocorrido ...", id="ascii-ellipsis"),
    pytest.param("Se houver autorização:", id="condition-variant"),
    pytest.param("É falso que o fato a seguir tenha ocorrido.", id="negation-variant"),
    pytest.param("O fato abaixo é hipotético:", id="hypothesis"),
    pytest.param("Informação desmentida sobre o fato a seguir:", id="disavowal"),
    pytest.param("Retratação do fato anterior.", id="backward-scope"),
    pytest.param("Retratação sobre o fato abaixo:", id="forward-retraction"),
    pytest.param("Alegação de terceiros sobre o fato a seguir:", id="third-party"),
])
@pytest.mark.parametrize(("text", "independent"), [
    pytest.param(TRADE, REGULATION, id="trade-three"),
    pytest.param(REGULATION, TRADE, id="regulatory-three"),
])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_context_applies_only_to_the_fact_it_qualifies(catalog, prefix, text, independent, newline):
    engine = OfficialEventExtractor(catalog)
    separator = newline * 2
    text = text.replace("\n", newline)
    independent = independent.replace("\n", newline)
    qualified = separator.join((prefix, text))
    expected = [text] if prefix == "Retratação do fato anterior." else []
    assert [e.description for e in engine.extract((document(qualified),), as_of=CUT)] == expected

    content = separator.join((qualified, F, independent))
    events = engine.extract((document(content),), as_of=CUT)
    assert [e.description for e in events] == [*expected, F, independent]
    assert all(content[e.content_start:e.content_end] == e.description for e in events)


def test_intervening_independent_fact_is_preserved(catalog):
    text = TRADE.replace("\n\ncomercial.", f"\n\n{F}\n\ncomercial.")
    events = OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT)
    assert [event.description for event in events] == [F]


def test_two_independent_events_keep_separate_evidence(catalog):
    content = TRADE + "\n\n" + REGULATION
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert [event.description for event in events] == [TRADE, REGULATION]
    assert [(event.content_start, event.content_end) for event in events] == [
        (0, len(TRADE)), (len(TRADE) + 2, len(content)),
    ]


def test_cutoff_and_reordered_revision_replay(catalog):
    engine = OfficialEventExtractor(catalog)
    first = document(TRADE)
    second = document(REGULATION, revision=2, received_at=CUT)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))

    events = engine.extract((first, second), as_of=CUT)
    assert [(event.revision, event.content_sha256, event.description) for event in events] == [
        (1, first.content_sha256, TRADE), (2, second.content_sha256, REGULATION),
    ]
    assert engine.extract((second, first, first), as_of=CUT) == events
