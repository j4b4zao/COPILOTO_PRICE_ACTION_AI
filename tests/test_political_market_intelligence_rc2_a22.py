"""Restricted fiscal and three-fragment economic measure continuity."""

from dataclasses import replace
from datetime import timedelta

import pytest

from audit.pmi_rc2_a18 import CASES as A18_CASES
from audit.pmi_rc2_a21 import CASES as A21_CASES
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


FISCAL = next(text for name, text, _, _ in A18_CASES if name == "fiscal-three-breaks")
MEASURE = next(text for name, text, _, _ in A18_CASES if name == "measure-arbitrary-wrap")
REGULATION = "A CVM publicou a Resolução nº 716/2025."
CONTEXT_CASES = [text for name, text, _, _ in A21_CASES if name.startswith("unmarked-")]


@pytest.mark.parametrize(("event_text", "category"), [
    (FISCAL, "FISCAL_COMMUNICATION"),
    (MEASURE, "ECONOMIC_MEASURE"),
    ("O Tesouro Nacional divulgou o resultado primário com\r\n\r\n\r\n"
     "superávit de R$ 34 milhões.", "FISCAL_COMMUNICATION"),
])
def test_literals_offsets_independent_events_and_replay(catalog, event_text, category):
    content = "Nota 📄.\r\n\r\n  " + event_text + "\r\n\r\n" + REGULATION
    doc = document(content)
    engine = OfficialEventExtractor(catalog)
    event, independent = engine.extract((doc,), as_of=CUT)
    assert event.category.value == category
    assert event.description == content[event.content_start:event.content_end] == event_text
    assert event.content_start == content.index(event_text)
    assert event.content_sha256 == doc.content_sha256
    assert (event.source_id, event.document_id, event.revision) == doc.key
    assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
    assert event.state is DocumentState.UNVERIFIED
    assert independent.description == REGULATION
    assert engine.extract((doc, doc), as_of=CUT) == (event, independent)


@pytest.mark.parametrize("content", [
    *CONTEXT_CASES,
    "Premissa contrafactual para o exercício.\n\n" + MEASURE,
    "Rascunho de circulação interna.\n\n" + FISCAL,
    "Exemplo do anúncio projetado para amanhã.\n\n" + MEASURE,
    "A narrativa a seguir foi apresentada por uma associação.\n\n" + FISCAL,
    "Hipótese:\n" + FISCAL,
    "Simulação:\n" + MEASURE,
    "Minuta:\n" + FISCAL,
    "Projeção:\n" + MEASURE,
    "Se a condição se cumprir:\n" + FISCAL,
    "A afirmação abaixo é uma alegação de terceiros.\n\n" + MEASURE,
    FISCAL.replace("R$", "US$"),
    FISCAL.replace("R$", "não R$"),
    FISCAL.replace("de\n", "de.\n"),
    FISCAL + "\n\nRetratação: a informação acima foi desmentida.",
    MEASURE + "\n\nA nota desmente a frase anterior.",
    MEASURE.replace("anunciou", "não anunciou"),
    MEASURE.replace("anunciou", "A comissão anunciou"),
    MEASURE.replace("anunciou", "## Resultados oficiais\n\nanunciou"),
    MEASURE.replace("anunciou", "## Agenda fiscal\nanunciou"),
    MEASURE.replace("anunciou", "Hipótese intermediária:\nanunciou"),
    MEASURE.replace("aumento\n\n", "aumento.\n\n"),
])
def test_context_and_incompatible_fragments_prevent_extraction(catalog, content):
    assert OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT) == ()


def test_cutoff_and_provenance_before_multifragment_extraction(catalog):
    doc = document(MEASURE, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    assert len(engine.extract((doc,), as_of=CUT)) == 1
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((doc,), as_of=CUT - timedelta(microseconds=1))
    for field, value in (("state", "UNVERIFIED"), ("content_sha256", "0" * 64)):
        altered = replace(doc)
        object.__setattr__(altered, field, value)
        with pytest.raises(ValueError, match="provenance"):
            engine.extract((altered,), as_of=CUT)
