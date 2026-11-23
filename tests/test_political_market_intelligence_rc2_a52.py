"""Literal fragmented-resolution evidence and the synthetic R4 matrix."""

from collections import Counter
from datetime import timedelta
from hashlib import sha256
import json
from unicodedata import normalize

import pytest

from political_market_intelligence.official_event_extractor import DocumentState, OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document
from tests.test_political_market_intelligence_rc2_a51 import P08


INSTRUCTION = "A CVM editou a Instrução nº\n\n734/\n\n2016."
OTHER = "A CVM alterou a Resolução CVM nº 506/2019."


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize("year_gap", ["", "\n", "\n\n"], ids=["continuous", "line", "paragraph"])
def test_p08_literal_identity_and_replay(catalog, form, newline, year_gap):
    resolution = normalize(form, P08.replace("311/\n\n", "311/" + year_gap)).replace("\n", newline)
    instruction = normalize(form, INSTRUCTION).replace("\n", newline)
    other = normalize(form, OTHER)
    separator = newline * 2
    prefix = "Arquivo 🗂️ a\u0327\u0301." + separator + "  "
    first = document(prefix + separator.join((resolution, other, instruction)))
    second = document(separator.join((instruction, resolution)), revision=2, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))
    events = engine.extract((first, second), as_of=CUT)
    expected = (resolution, other, instruction, instruction, resolution)
    assert len({event.event_id for event in events}) == len(expected)
    assert events[0].content_start == len(prefix)
    for event, literal, doc in zip(events, expected, (first, first, first, second, second), strict=True):
        assert event.category.value == "REGULATORY_CHANGE"
        assert event.description == literal == doc.content[event.content_start:event.content_end]
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
        assert event.content_sha256 == doc.content_sha256 == sha256(doc.content.encode()).hexdigest()
        identity = json.dumps((*doc.key, doc.content_sha256, event.content_start,
                               event.content_end, event.category.value))
        assert event.event_id == sha256(identity.encode()).hexdigest()
    assert engine.extract((second, first, first), as_of=CUT) == events


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("interruption", [
    OTHER,
    "## Ano do ato",
    "| Ano | Origem |\n| 2022 | Resolução nº 45 |",
    "Nota de paginação: 2022 é o ano da resolução nº 45.",
    "A Instrução nº 15 é de outro ato.",
    "Retificação: onde se lê 311/2022, leia-se 311/2023.",
    "Hipótese:",
], ids=["other-act", "heading", "table", "pagination", "reference", "correction", "hypothesis"])
def test_p08_does_not_join_interrupted_reference(catalog, form, interruption):
    content = normalize(form, P08.replace("311/\n\n", f"311/\n\n{interruption}\n\n"))
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    expected = (normalize(form, OTHER),) if interruption == OTHER else ()
    assert tuple(event.description for event in events) == expected
    assert all(content[event.content_start:event.content_end] == event.description for event in events)


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize(("body", "emit"), [
    ("É falso que o fato abaixo tenha ocorrido…\n\n" + P08, False),
    ("Se a diretoria aprovar a proposta:\n\n" + P08, False),
    ("Hipótese:\n\n" + P08, False),
    ("Simulação:\n\n" + P08, False),
    ("A informação abaixo é uma alegação de terceiros.\n\n" + P08, False),
    (P08 + "\n\nRetificação: onde se lê 311/2022, leia-se 311/2023.", False),
    ("Hipótese:\n\n## Deliberação registrada\n\n" + P08, True),
    ("Em retrospecto, A CVM publicou a Resolução CVM nº 311/2022.", True),
])
def test_p08_respects_semantic_guards(catalog, form, body, emit):
    content = normalize(form, body + "\n\n## Fatos documentados\n\n" + OTHER)
    expected = [normalize(form, body.removeprefix("Hipótese:\n\n## Deliberação registrada\n\n"))] if emit else []
    expected.append(normalize(form, OTHER))
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert [event.description for event in events] == expected
    assert all(content[event.content_start:event.content_end] == event.description for event in events)


# These are the 24 R4 case definitions, each expanded to four documents below.
FACTS = {
    "I": ("ECONOMIC_INDICATOR", "O IBGE divulgou o PIB de 2,9%."),
    "M": ("MONETARY_POLICY", "O Copom fixou a Selic em 9,75% ao ano."),
    "X": ("FOREIGN_TRADE", "O MDIC publicou o boletim da balança comercial."),
    "G": ("ECONOMIC_MEASURE", "O Governo Federal anunciou o aumento do IOF."),
    "F": ("FISCAL_COMMUNICATION", "O Tesouro Nacional informou superávit primário de R$ 13 milhões."),
    "I2": ("ECONOMIC_INDICATOR", "O IBGE divulgou o IPCA de 0,39%."),
    "R": ("REGULATORY_CHANGE", "A CVM publicou a Resolução CVM nº 482/2023."),
    "J": ("REGULATORY_CHANGE", INSTRUCTION),
    "P08": ("REGULATORY_CHANGE", P08.replace("311", "627").replace("2022", "2021")),
    "R2": ("REGULATORY_CHANGE", OTHER),
}
R4_CASES = [
    pytest.param(["J"], ["J"], id="p06"),
    pytest.param(["R"], ["R"], id="p07"),
    pytest.param(["P08"], ["P08"], id="p08"),
]
for label, heading, key in (
    ("negation", "Negação:", "M"),
    ("hypothesis", "Hipótese:", "F"),
    ("condition", "Se a condição se cumprir:", "I"),
    ("simulation", "Simulação:", "X"),
    ("third-party", "A informação a seguir é uma alegação da associação.", "G"),
    ("projected", "Projeção para o ano seguinte:", "R"),
):
    after = "G" if key == "M" else "M"
    R4_CASES.append(pytest.param(["I2", heading, key, "## Decisões oficiais", after], ["I2", after], id=label))
    if label != "third-party":
        R4_CASES.append(pytest.param([heading + "\n@" + key], [], id=label + "-single"))

R4_CASES += [
    pytest.param(["Hipótese:", "G", "## Seção  factual:", "I", "X"], ["I", "X"], id="hypothesis-with-factual-reset"),
    pytest.param(["G", "A associação apresentou a seguinte alegação:", "R", "R2", "I"], ["G", "I"], id="third-party-independent"),
    pytest.param(["F", "I", "Retratação: o dado acima não ocorreu.", "M"], ["F", "M"], id="retroactive"),
    pytest.param(["J", "R", "Retificação: onde se lê 734/2016, leia-se 734/2017.", "G"], ["R", "G"], id="correction-specific"),
    pytest.param(["J", "Hipótese:", "Retificação: onde se lê 734/2016, leia-se 734/2017.", "## Resultados oficiais", "X"],
                 ["J", "X"], id="correction-hypothetical"),
    pytest.param(["I", "J", "Nota de paginação: 2016 é o ano da resolução nº 311.", "G"], ["I", "G"], id="pagination-related"),
    pytest.param(["I", "J", "Nota de paginação: 2015 é o ano da resolução nº 311.", "G"], ["I", "J", "G"], id="pagination-unrelated"),
    pytest.param(["Em retrospecto, @R", "I"], ["R", "I"], id="historical"),
    pytest.param(["Em retrospecto, A CVM publicou a Resolução CVM nº 482/2023 em 2028.", "M"], ["M"], id="historical-future"),
    pytest.param(["A CVM não publicou a Resolução CVM nº 482/2023.", "X"], ["X"], id="explicit-negative"),
]


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
@pytest.mark.parametrize(("blocks", "wanted"), R4_CASES)
def test_r4_synthetic_matrix(catalog, form, newline, blocks, wanted, request):
    def fact(key):
        category, literal = FACTS[key]
        if category == "REGULATORY_CHANGE":
            literal = normalize(form, literal)
        return category, literal.replace("\n", newline)

    def render(block):
        if block in FACTS:
            return fact(block)[1]
        heading, marker, key = block.partition("@")
        return normalize(form, heading).replace("\n", newline) + (fact(key)[1] if marker else "")

    gap = newline * 2
    content = "Arquivo 🗂️ a\u0327\u0301." + gap + gap.join(map(render, blocks))
    label = request.node.callspec.id.rsplit("-", 2)[0]
    doc = document(content, document_id=label + form + str(len(newline)))
    engine = OfficialEventExtractor(catalog)
    events = engine.extract((doc,), as_of=CUT)
    actual = Counter()
    for event in events:
        assert 0 <= event.content_start < event.content_end <= len(content)
        assert event.description == content[event.content_start:event.content_end]
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
        assert event.content_sha256 == doc.content_sha256 == sha256(content.encode()).hexdigest()
        identity = json.dumps((*doc.key, doc.content_sha256, event.content_start,
                               event.content_end, event.category.value))
        assert event.event_id == sha256(identity.encode()).hexdigest()
        literal = event.description
        if blocks[0] == "Em retrospecto, @R":
            literal = literal.removeprefix("Em retrospecto, ")
        actual[event.category.value, literal] += 1
    assert actual == Counter(map(fact, wanted))
    assert engine.extract((doc, doc), as_of=CUT) == events
