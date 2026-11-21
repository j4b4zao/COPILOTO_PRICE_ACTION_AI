"""Controlled language expansion and A16 guard preservation."""

import pytest

from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import (
    CUT, IND, MON, REG, document, catalog,
)


RATE = "O Copom elevou a Selic para 14,25%."
PRICE = "O IBGE divulgou o IPCA de 0,46%."


@pytest.mark.parametrize(("content", "categories"), [
    ("3. Resumo executivo\n" + RATE, (MON,)),
    ("# Notas da reunião\n" + RATE, (MON,)),
    ("Simulação:\n" + PRICE + "\n## Deliberação registrada\n" + RATE, (MON,)),
    ("Não se pode negar que o Copom elevou a Selic para 14,25%.", (MON,)),
    ("Não é verdade que a CVM não tenha revogado a Instrução nº 73/2025.", (REG,)),
    ("Em retrospecto, o IBGE divulgou o IPCA de 0,46%.", (IND,)),
    (RATE[:-1] + " em 2023.", (MON,)),
    (RATE.replace("14,25", "14,\r\n  25"), (MON,)),
    ("A CVM revo-\ngou a Instrução nº 73/2025.", (REG,)),
    ("• " + PRICE, (IND,)),
    (RATE[:-1] + " e o IBGE divulgou o IPCA de 0,46%.", (MON, IND)),
    (PRICE[:-1] + ", enquanto o Copom elevou a Selic para 14,25%.", (IND, MON)),
])
def test_expanded_recognition_preserves_literal_evidence(catalog, content, categories):
    doc = document(content)
    extractor = OfficialEventExtractor(catalog)
    events = extractor.extract((doc,), as_of=CUT)
    assert tuple(event.category.value for event in events) == categories
    assert extractor.extract((doc, doc), as_of=CUT) == events
    assert len({event.event_id for event in events}) == len(events)
    for event in events:
        assert event.description == content[event.content_start:event.content_end]
        assert event.content_sha256 == doc.content_sha256
        assert (event.source_id, event.document_id, event.revision) == doc.key
    if len(events) == 2:
        assert events[0].content_end < events[1].content_start


@pytest.mark.parametrize("content", [
    "Minuta:\n## Resumo executivo\n" + RATE,
    "Minuta:\n## Notas da reunião\n" + RATE,
    "Hipótese:\n" + RATE[:-1] + " e o IBGE divulgou o IPCA de 0,46%.",
    "Segundo a associação, " + RATE[:-1] + " e o IBGE divulgou o IPCA de 0,46%.",
    RATE[:-1] + " e o IBGE divulgará o IPCA amanhã.",
    RATE[:-1] + " e o IBGE não divulgou o IPCA de 0,46%.",
    RATE[:-1] + " em 2027.",
    "Não se pode negar que o Copom não elevou a Selic para 14,25%.",
])
def test_expansion_does_not_extract_partial_or_nonfactual_claims(catalog, content):
    assert OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT) == ()


def test_retraction_of_compound_preserves_independent_statement(catalog):
    compound = RATE[:-1] + " e o IBGE divulgou o IPCA de 0,46%."
    content = PRICE + "\n" + compound + " A nota desmente a frase anterior."
    event, = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert event.description == PRICE
    assert event.content_start == 0
