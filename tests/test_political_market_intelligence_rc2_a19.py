"""Fiscal continuation and bounded attribution against the A19 contract."""

from dataclasses import replace
from datetime import timedelta

import pytest

from audit.pmi_rc2_a15 import TEXT
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventCategory, OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


LEAD = "O Tesouro Nacional divulgou o resultado primário com"
COMPLEMENT = "superávit de R$ 18 milhões."
FISCAL = LEAD + "\r\n \t\r\n" + COMPLEMENT
MONETARY = "O Copom manteve a Selic em 11,45%."
REGULATION = "A CVM publicou a Resolução nº 321/2026."
CLAIM = "A informação abaixo é uma alegação da associação."


@pytest.mark.parametrize("content", [TEXT[37][1], FISCAL])
def test_fiscal_continuation_preserves_literal_span_and_replay(catalog, content):
    text = "Introdução.\r\n\r\n  " + content + "\r\n\r\n" + REGULATION
    doc = document(text)
    extractor = OfficialEventExtractor(catalog)
    events = extractor.extract((doc,), as_of=CUT)
    assert [event.description for event in events] == [content, REGULATION]
    assert events[0].category is OfficialEventCategory.FISCAL_COMMUNICATION
    assert events == extractor.extract((doc, doc), as_of=CUT)
    for event in events:
        assert text[event.content_start:event.content_end] == event.description
        assert event.content_sha256 == doc.content_sha256
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert event.state is DocumentState.UNVERIFIED


@pytest.mark.parametrize("content", [
    LEAD + ".\n\n" + COMPLEMENT,
    LEAD + "\n\n## Resultados oficiais\n\n" + COMPLEMENT,
    LEAD + "\n\n## Assunto diferente\n" + COMPLEMENT,
    LEAD + "\n\nHipótese alternativa:\n" + COMPLEMENT,
    LEAD + "\n\nnão houve " + COMPLEMENT,
    "Hipótese:\n" + FISCAL,
    "Minuta para aprovação:\n" + FISCAL,
    "Projeção para o semestre seguinte:\n" + FISCAL,
    "Exercício com dados inventados.\n\n" + FISCAL,
    FISCAL + "\n\nRetratação: a informação acima foi desmentida.",
    "O Tesouro Nacional não divulgou o resultado primário com\n\n" + COMPLEMENT,
    LEAD + "\n\n18 servidores participaram da reunião.",
])
def test_unsafe_fiscal_bridges_are_rejected(catalog, content):
    assert OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT) == ()


def test_claim_does_not_suppress_independent_authority_or_factual_section(catalog):
    quoted = "Segundo o Copom, “" + MONETARY + "”"
    text = f"{CLAIM}\n\n{MONETARY}\n\n{quoted}\n\n## Fatos documentados\n{REGULATION}"
    events = OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT)
    assert [event.description for event in events] == [quoted, REGULATION]
    assert events[0].category is OfficialEventCategory.MONETARY_POLICY


@pytest.mark.parametrize("text", [
    CLAIM + "\n\n" + MONETARY,
    CLAIM + "\n\nTrecho reproduzido.\n\n" + MONETARY,
    CLAIM + "\n\n" + MONETARY + " " + REGULATION,
    CLAIM + "\n\nSegundo o Copom, “" + MONETARY + "”",
    "Segundo a associação, “" + MONETARY + "”",
    "Segundo a CVM, “" + MONETARY + "”",
])
def test_third_party_or_mismatched_attribution_is_not_emitted(catalog, text):
    assert OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT) == ()


def test_cutoff_and_provenance_gate_apply_before_joining(catalog):
    doc = document(FISCAL, received_at=CUT)
    extractor = OfficialEventExtractor(catalog)
    assert len(extractor.extract((doc,), as_of=CUT)) == 1
    with pytest.raises(ValueError, match="cutoff"):
        extractor.extract((doc,), as_of=CUT - timedelta(microseconds=1))
    tampered = replace(doc)
    object.__setattr__(tampered, "content_sha256", "0" * 64)
    with pytest.raises(ValueError, match="provenance"):
        extractor.extract((tampered,), as_of=CUT)
