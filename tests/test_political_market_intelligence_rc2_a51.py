"""Canonical regulatory comparisons with offsets in the unchanged document."""

from datetime import timedelta
from hashlib import sha256
from unicodedata import normalize

import pytest

from political_market_intelligence.official_document_normalizer import DocumentState
from political_market_intelligence.official_event_extractor import OfficialEventExtractor
from tests.test_political_market_intelligence_rc2_a14 import CUT, catalog, document
from tests.test_political_market_intelligence_rc2_a50 import (
    CLAIM, CONDITION, CORRECTION, FACTUAL, INSTRUCTION, RESOLUTION, SIMULATION,
    SUBJECT_TO_YEAR_NOTE, YEAR_NOTE,
)


@pytest.mark.parametrize("form", ["NFC", "NFD"])
@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_regulatory_evidence_uses_original_code_point_offsets(catalog, form, newline):
    prefix = normalize("NFD", "Edição 🗂️, sequência á̧.") + newline * 2 + "  "
    instruction = normalize(form, INSTRUCTION.replace("87/", "112/").replace("2018", "2017"))
    instruction = instruction.replace("\n", newline)
    resolution = normalize(form, RESOLUTION)
    first = document(prefix + instruction + newline * 2 + resolution)
    second = document(resolution, revision=2, received_at=CUT)
    engine = OfficialEventExtractor(catalog)
    with pytest.raises(ValueError, match="cutoff"):
        engine.extract((first, second), as_of=CUT - timedelta(microseconds=1))
    events = engine.extract((first, second), as_of=CUT)
    assert [event.category.value for event in events] == ["REGULATORY_CHANGE"] * 3
    assert [event.description for event in events] == [instruction, resolution, resolution]
    assert (events[0].content_start, events[0].content_end) == (
        len(prefix), len(prefix) + len(instruction),
    )
    assert events[1].content_start == len(prefix) + len(instruction) + 2 * len(newline)
    for event, doc in zip(events, (first, first, second), strict=True):
        assert doc.content[event.content_start:event.content_end] == event.description
        assert event.content_sha256 == doc.content_sha256 == sha256(doc.content.encode("utf-8")).hexdigest()
        assert (event.source_id, event.document_id, event.revision) == doc.key
        assert (event.published_at, event.available_at) == (doc.published_at, doc.received_at)
        assert event.state is DocumentState.UNVERIFIED
    assert engine.extract((second, first, first), as_of=CUT) == events


P08 = "A CVM publicou a Resolução CVM nº\n\n311/\n\n2022."


@pytest.mark.parametrize("blocks", [
    ("É falso que o fato abaixo tenha ocorrido…", INSTRUCTION),
    (CONDITION, INSTRUCTION),
    ("Hipótese:", INSTRUCTION),
    (CLAIM, INSTRUCTION, INSTRUCTION.replace("87/", "193/")),
    (SIMULATION, INSTRUCTION, RESOLUTION),
    (INSTRUCTION, CORRECTION),
    (SUBJECT_TO_YEAR_NOTE, YEAR_NOTE),
    (INSTRUCTION.replace("2018.", "## Ano da Resolução nº 97\n\n2018."),),
    (INSTRUCTION.replace("87/", "Resolução nº 87/"),),
    (P08,),
], ids=[
    "negation", "condition", "hypothesis", "third-party", "simulation",
    "correction", "other-act-year", "intervening-heading", "other-act-number", "P08",
])
@pytest.mark.parametrize("form", ["NFC", "NFD"])
def test_canonical_comparison_preserves_semantic_guards(catalog, blocks, form):
    independent = normalize(form, RESOLUTION)
    negative = normalize(form, "\n\n".join(blocks))
    engine = OfficialEventExtractor(catalog)
    expected = (negative,) if blocks == (P08,) else ()
    assert tuple(event.description for event in engine.extract(
        (document(negative),), as_of=CUT,
    )) == expected
    content = negative + "\n\n" + normalize(form, FACTUAL) + "\n\n" + independent
    events = engine.extract((document(content),), as_of=CUT)
    assert len({event.event_id for event in events}) == len(events)
    for event, literal in zip(events, (*expected, independent), strict=True):
        assert content[event.content_start:event.content_end] == event.description == literal
