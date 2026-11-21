"""Priority-one fiscal and economic measure paragraph continuity."""

from datetime import timedelta

import pytest

from audit.pmi_rc2_a15 import CATEGORIES
from audit.pmi_rc2_a21 import CASES, F3, E3, R, X
from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document


PRIORITY = {
    "fiscal-three": "F",
    "line-wrap-plus-paragraph-break": "F",
    "literal-offset-after-emoji": "F",
    "measure-three": "E",
    "completed-fact-before-fragments": "E",
}


@pytest.mark.parametrize(("label", "content", "wanted"), [
    pytest.param(label, content, wanted, id=label)
    for label, content, wanted, _ in CASES if label in PRIORITY
])
def test_priority_one_literal_evidence_and_replay(catalog, label, content, wanted):
    engine = OfficialEventExtractor(catalog)
    doc = document(content)
    events = engine.extract((doc,), as_of=CUT)
    assert tuple(event.category.value for event in events) == tuple(CATEGORIES[c] for c in wanted)
    target, = [event for event in events if event.category.value == CATEGORIES[PRIORITY[label]]]
    literal = F3 if PRIORITY[label] == "F" else E3
    if label == "line-wrap-plus-paragraph-break":
        literal = literal.replace("Tesouro Nacional", "Tesouro\nNacional")
    assert target.description == literal
    assert target.content_start == content.index(literal)
    for event in events:
        assert event.description == content[event.content_start:event.content_end]
        assert event.content_sha256 == doc.content_sha256
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
    assert engine.extract((doc, doc), as_of=CUT) == events


@pytest.mark.parametrize("text", [
    F3.replace("R$", "US$"),
    F3.replace("milhões", "toneladas"),
    E3.replace("a suspensão", "A comissão recomendou a suspensão"),
    F3.replace("com superávit", "## Resultados oficiais\n\ncom superávit"),
    E3.replace("a suspensão", "## Nota interna\na suspensão"),
    E3.replace("anunciou", "não anunciou"),
    E3.replace("a suspensão", "Hipótese intermediária:\na suspensão"),
    "Hipótese:\n" + F3,
    "Minuta:\n" + E3,
    "Se a condição se cumprir:\n" + E3,
    E3.replace("do IPI.", "do IPI se a medida for aprovada."),
    F3 + "\n\nRetratação: a informação acima foi desmentida.",
    E3 + "\n\nA nota desmente a frase anterior.",
    "A afirmação abaixo é uma alegação de terceiros.\n\n" + E3,
])
def test_incompatible_or_qualified_continuations_are_not_emitted(catalog, text):
    assert OfficialEventExtractor(catalog).extract((document(text),), as_of=CUT) == ()


def test_independent_fact_between_fragments_is_preserved(catalog):
    content = E3.replace("\n\na suspensão", f"\n\n{R}\n\na suspensão") + "\n\n" + X
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert [event.description for event in events] == [R, X]


def test_two_reconstructed_events_keep_separate_evidence(catalog):
    content = F3 + "\n\n" + E3
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert [event.description for event in events] == [F3, E3]
    assert [(event.content_start, event.content_end) for event in events] == [
        (0, len(F3)), (len(F3) + 2, len(content)),
    ]


def test_reconstructed_revisions_respect_cutoff_and_replay_order(catalog):
    engine = OfficialEventExtractor(catalog)
    first = document(F3)
    second = document(E3, revision=2, received_at=CUT)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))

    events = engine.extract((first, second), as_of=CUT)
    assert [(event.revision, event.content_sha256, event.description) for event in events] == [
        (1, first.content_sha256, F3), (2, second.content_sha256, E3),
    ]
    assert engine.extract((second, first, first), as_of=CUT) == events
