"""Pagination and historical-context controls, including the 17 A53 documents."""

from datetime import timedelta
from hashlib import sha256
import json
from unicodedata import normalize

import pytest

from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


GAP = "\n\n"
PREFIX = "Protocolo 📄 a\u0327\u0301." + GAP
HEAD = "A CVM publicou a Resolução CVM nº"
ACT = HEAD + GAP + "482/" + GAP + "2019."
OTHER = HEAD + " 726/2020."
INSTRUCTION = "A CVM editou a Instrução nº\n\n815/\n\n2018."
INDICATOR = "O IBGE divulgou o IPCA de 0,71%."
NOTE = "Nota de paginação: 2019 é o ano da resolução nº 726."
CORRECTION = "Retificação: onde se lê 482/2019, leia-se 482/2021."
HISTORICAL = "Em retrospecto, " + ACT
MIXED = normalize("NFD", HEAD) + "\r\n\r\n\t482/\r\n  2019."
SECOND = HEAD + GAP + "483/\n2017."


def check_evidence(engine, doc, expected):
    events = engine.extract((doc,), as_of=CUT)
    assert tuple(event.description for event in events) == expected
    for event in events:
        category = "ECONOMIC_INDICATOR" if event.description == INDICATOR else "REGULATORY_CHANGE"
        assert event.category.value == category
        assert 0 <= event.content_start < event.content_end <= len(doc.content)
        assert doc.content[event.content_start:event.content_end] == event.description
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert event.content_sha256 == doc.content_sha256 == sha256(doc.content.encode("utf-8")).hexdigest()
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
        identity = json.dumps((*doc.key, doc.content_sha256, event.content_start, event.content_end, category))
        assert event.event_id == sha256(identity.encode("utf-8")).hexdigest()
    assert engine.extract((doc, doc), as_of=CUT) == events
    return events


@pytest.mark.parametrize(("body", "expected"), [
    pytest.param(MIXED, (MIXED,), id="fragment-mixed"),
    pytest.param(GAP.join((ACT, SECOND)), (ACT, SECOND), id="two-fragmented"),
    pytest.param(GAP.join((INSTRUCTION, MIXED, INDICATOR)), (INSTRUCTION, MIXED, INDICATOR),
                 id="instruction-resolution-indicator"),
    pytest.param(GAP.join((HEAD, "482/", OTHER, "2019.")), (OTHER,), id="cross-act"),
    pytest.param(GAP.join((HEAD, "482/", "## Ano da Resolução CVM nº 726", "2019.")), (),
                 id="cross-year-heading"),
    pytest.param(GAP.join((HEAD, "482/", "| Ato | Ano |\n| 726 | 2019 |", INDICATOR)), (INDICATOR,),
                 id="cross-table"),
    pytest.param(GAP.join((HEAD, "482/", NOTE, "2019.")), (), id="cross-pagination"),
    pytest.param(GAP.join((INDICATOR, HEAD.replace("publicou", "não publicou"), "482/\n2019.", OTHER)),
                 (INDICATOR, OTHER), id="negated"),
    pytest.param(normalize("NFD", "Hipótese:") + "\n" + ACT + GAP + "## Deliberação registrada\n" + OTHER,
                 (OTHER,), id="hypothesis-reset"),
    pytest.param("Se a diretoria aprovar a proposta:\n" + ACT + GAP + OTHER, (OTHER,),
                 id="condition-next-independent"),
    pytest.param(GAP.join(("Fórmula de simulação para teste interno:", MIXED, "## Resultados oficiais", INDICATOR)),
                 (INDICATOR,), id="simulation-reset"),
    pytest.param(GAP.join((normalize("NFD", "A narrativa a seguir foi apresentada por uma associação:"),
                           ACT, OTHER, "## Fatos documentados", INSTRUCTION)), (INSTRUCTION,), id="third-party-reset"),
    pytest.param(GAP.join((OTHER, ACT, normalize("NFD", CORRECTION), INDICATOR)), (OTHER, INDICATOR),
                 id="correction-specific"),
    pytest.param(GAP.join((OTHER, ACT, CORRECTION.replace("482/2019", "482/2018"))), (OTHER, ACT),
                 id="correction-same-number-other-year"),
    pytest.param("Em retrospecto, " + OTHER, ("Em retrospecto, " + OTHER,), id="historical-contiguous"),
    pytest.param(GAP.join((HISTORICAL, INDICATOR)), (HISTORICAL, INDICATOR), id="historical-fragmented"),
    pytest.param(GAP.join((ACT, NOTE, INDICATOR)), (INDICATOR,), id="conflicting-pagination-after"),
])
def test_a53_independent_scenarios(catalog, body, expected):
    check_evidence(OfficialEventExtractor(catalog), document(PREFIX + body), expected)


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize(("blocks", "expected"), [
    pytest.param((ACT, NOTE), (), id="conflicting-note"),
    pytest.param((ACT, NOTE.replace("2019", "2021")), (ACT,), id="different-year"),
    pytest.param((ACT, NOTE.replace("726", "0482")), (ACT,), id="same-act"),
    pytest.param((ACT, OTHER, NOTE), (ACT, OTHER), id="intervening-act"),
    pytest.param((ACT.replace("482/\n\n", "482/\n"), NOTE), (), id="single-year-break"),
    pytest.param((ACT.replace("482/\n\n", "482/"), NOTE),
                 (ACT.replace("482/\n\n", "482/"),), id="continuous-number-year"),
    pytest.param((HISTORICAL,), (HISTORICAL,), id="historical"),
    pytest.param((HISTORICAL, NOTE), (), id="historical-conflicting-note"),
    pytest.param(("Na série anterior, " + ACT,), ("Na série anterior, " + ACT,), id="historical-alternate"),
    pytest.param(("Em retrospecto, A CVM não publicou" + ACT[len("A CVM publicou"):],), (), id="negation"),
    pytest.param(("Hipótese:", HISTORICAL, "## Fatos documentados"), (), id="hypothesis"),
    pytest.param(("Se a diretoria aprovar a proposta:", HISTORICAL), (), id="condition"),
    pytest.param(("Fórmula de simulação para teste interno:", HISTORICAL, "## Fatos documentados"),
                 (), id="simulation"),
    pytest.param(("A afirmação abaixo é uma alegação de terceiros.", HISTORICAL, "## Fatos documentados"),
                 (), id="third-party"),
    pytest.param(("Em retrospecto, Resolução CVM nº" + GAP + "482/" + GAP + "2019.",),
                 (), id="reference-only"),
])
def test_a54_context_and_offsets(catalog, form, newline, blocks, expected):
    def variant(text):
        return normalize(form, text).replace("\n", newline)

    content = variant(PREFIX + GAP.join((*blocks, INDICATOR)))
    doc = document(content)
    engine = OfficialEventExtractor(catalog)
    events = check_evidence(engine, doc, tuple(map(variant, (*expected, INDICATOR))))
    if blocks == (HISTORICAL,):
        assert (events[0].content_start, events[0].content_end) == (
            len(variant(PREFIX)), len(variant(PREFIX + HISTORICAL)),
        )


def test_historical_resolution_revision_and_cutoff(catalog):
    first = document(HISTORICAL)
    second = document(HISTORICAL + GAP + NOTE, revision=2, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))
    events = check_evidence(engine, first, (HISTORICAL,))
    assert engine.extract((second, first, first), as_of=CUT) == events
