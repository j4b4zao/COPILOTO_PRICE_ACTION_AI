"""Semantic boundaries for the six unwanted emissions found by A49."""

from datetime import timedelta
from hashlib import sha256
from unicodedata import normalize

import pytest

from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


INSTRUCTION = "A CVM editou a Instrução nº\n\n87/\n\n2018."
SECOND = "A CVM editou a Instrução nº\n\n193/\n\n2019."
RESOLUTION = "A CVM publicou a Resolução CVM nº 211/2024."
FISCAL = "O Tesouro Nacional divulgou o resultado fiscal com déficit de R$ 12 milhões."
INDICATOR = "O IBGE divulgou o PIB de 1,6%."
CORRECTION = "Retificação: onde se lê 87/2018, leia-se 87/2019."
YEAR_NOTE = "Nota de paginação: 2022 é o ano da Resolução nº 97, listado na tabela seguinte."
CLAIM = "A afirmação abaixo é uma alegação de terceiros."
CONDITION = "Se a diretoria aprovar a proposta:"
SIMULATION = "Fórmula de simulação para teste interno:"
SUBJECT_TO_YEAR_NOTE = "A CVM editou a Instrução nº\n\n518/\n\n2022."
FACTUAL = "## Fatos documentados"


@pytest.mark.parametrize(("blocks", "expected"), [
    pytest.param((INSTRUCTION, CORRECTION), (), id="P13"),
    pytest.param((SUBJECT_TO_YEAR_NOTE, YEAR_NOTE), (), id="N15"),
    pytest.param((CLAIM, INSTRUCTION, SECOND, FACTUAL, RESOLUTION), (RESOLUTION,), id="P14"),
    pytest.param((CONDITION, INSTRUCTION), (), id="N10"),
    pytest.param((SIMULATION, FISCAL, INDICATOR), (), id="N16"),
    pytest.param((INSTRUCTION, SECOND, CORRECTION, RESOLUTION), (SECOND, RESOLUTION), id="specific"),
    pytest.param((SECOND, CORRECTION), (SECOND,), id="unrelated-correction"),
    pytest.param((SUBJECT_TO_YEAR_NOTE, YEAR_NOTE.replace("2022", "2023")), (SUBJECT_TO_YEAR_NOTE,),
                 id="unrelated-year"),
    pytest.param((SUBJECT_TO_YEAR_NOTE, RESOLUTION, YEAR_NOTE), (SUBJECT_TO_YEAR_NOTE, RESOLUTION),
                 id="year-note-does-not-cross-a-fact"),
    pytest.param((CLAIM, INSTRUCTION, SECOND, INDICATOR), (INDICATOR,), id="independent-indicator"),
    pytest.param((CONDITION, INSTRUCTION, FACTUAL, RESOLUTION), (RESOLUTION,), id="condition-then-fact"),
    pytest.param(("Hipótese:", INSTRUCTION, FACTUAL, RESOLUTION), (RESOLUTION,), id="hypothesis-then-fact"),
    pytest.param((SIMULATION, FISCAL, INDICATOR, FACTUAL, RESOLUTION), (RESOLUTION,), id="simulation-then-fact"),
    pytest.param((INSTRUCTION, "Hipótese:", CORRECTION), (INSTRUCTION,), id="hypothetical-correction"),
    pytest.param((INSTRUCTION, CONDITION, CORRECTION, FACTUAL, RESOLUTION), (INSTRUCTION, RESOLUTION),
                 id="conditional-correction"),
])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_semantic_boundaries(catalog, blocks, expected, newline):
    content = "\n\n".join(blocks).replace("\n", newline)
    doc = document(content)
    engine = OfficialEventExtractor(catalog)
    events = engine.extract((doc,), as_of=CUT)
    assert [event.description for event in events] == [text.replace("\n", newline) for text in expected]
    for event in events:
        assert content[event.content_start:event.content_end] == event.description
        assert event.content_sha256 == doc.content_sha256 == sha256(content.encode("utf-8")).hexdigest()
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
    assert engine.extract((doc, doc), as_of=CUT) == events


@pytest.mark.parametrize("blocks", [
    (INSTRUCTION, normalize("NFD", CORRECTION)),
    (SUBJECT_TO_YEAR_NOTE, normalize("NFD", YEAR_NOTE)),
    (normalize("NFD", SIMULATION), FISCAL, INDICATOR),
])
def test_nfd_negative_context_only(catalog, blocks):
    assert OfficialEventExtractor(catalog).extract((document("\n\n".join(blocks)),), as_of=CUT) == ()


def test_correction_in_later_revision_respects_cutoff_and_document_scope(catalog):
    first = document(INSTRUCTION)
    second = document(INSTRUCTION + "\n\n" + CORRECTION, revision=2, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((second, first), as_of=CUT - timedelta(microseconds=1))
    events = engine.extract((first, second), as_of=CUT)
    assert [(event.revision, event.description) for event in events] == [(1, INSTRUCTION)]
    assert engine.extract((second, first, first), as_of=CUT) == events
