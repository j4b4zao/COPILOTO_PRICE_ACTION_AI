"""A13 synthetic reference matrix and A14 context and evidence checks."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from political_market_intelligence.official_document_normalizer import DocumentObservation, DocumentState
from political_market_intelligence.official_event_extractor import ExtractedOfficialEvent, OfficialEventExtractor
from political_market_intelligence.official_ingestion_service import OfficialIngestionService
from political_market_intelligence.official_source_catalog import OfficialSource, OfficialSourceCatalog, OfficialSourceKind
from political_market_intelligence.event_model import EventCategory


T = datetime(2026, 11, 21, 12, tzinfo=timezone.utc)
CUT = T + timedelta(minutes=2)
M = "O Copom manteve a taxa Selic em 12,25% ao ano."
I = "O IBGE divulgou o IPCA de 0,25%."
F = "O Tesouro Nacional divulgou o resultado primário com déficit de R$ 2 bilhões."
R = "A CVM publicou a Resolução nº 123/2026."
X = "A Secex publicou o boletim da balança comercial."
E = "O Governo Federal anunciou a redução do IPI."
MON, IND, FIS, REG, TRADE, MEASURE = (
    "MONETARY_POLICY", "ECONOMIC_INDICATOR", "FISCAL_COMMUNICATION",
    "REGULATORY_CHANGE", "FOREIGN_TRADE", "ECONOMIC_MEASURE",
)


def document(content, **kwargs):
    return DocumentObservation(**(dict(
        source_id="fixture", document_id="x", revision=1, title="Fixture",
        content=content, published_at=T, received_at=T + timedelta(minutes=1),
    ) | kwargs))


@pytest.fixture
def catalog():
    return OfficialSourceCatalog((OfficialSource(
        source_id="fixture", institution="Fixture", country_code="BR",
        kind=OfficialSourceKind.COMMUNICATION, candidate_url="https://example.org",
        capabilities={EventCategory.CONFIRMED_FACT},
    ),))


@pytest.mark.parametrize(("content", "expected"), [
    ("O Banco Central reduziu a Selic para 12,25%.", (MON,)),
    (M, (MON,)), (I, (IND,)), (F, (FIS,)), (R, (REG,)), (X, (TRADE,)), (E, (MEASURE,)),
    (M + "\n" + I, (MON, IND)),
    (M + " " + I, (MON, IND)),
    ("Documento recebido para arquivamento.", ()),
    (M.replace("taxa Selic", "taxa\nSelic"), (MON,)),
    ("O Copom decidiu manter a taxa Selic em 12,25% ao ano.", (MON,)),
    ("O IBGE informou que o IPCA foi de 0,25%.", (IND,)),
    ("O Tesouro Nacional informou superávit primário de R$ 3 bilhões.", (FIS,)),
    ("A CVM editou a Resolução CVM nº 123/2026.", (REG,)),
    ("O MDIC divulgou os dados da balança comercial.", (TRADE,)),
    ("O Governo Federal anunciou que reduziu o IPI.", (MEASURE,)),
    ("Copom, Selic, IPCA e IPI.", ()),
    ("O Copom não manteve a taxa Selic em 12,25% ao ano.", ()),
    ("O Copom poderá manter a taxa Selic em 12,25% ao ano.", ()),
    ("Hipótese de treinamento (evento fictício):\n" + M, ()),
    ("Afirmação desmentida pelo comunicado:\n" + I, ()),
    ("Minuta fictícia para divulgação futura:\n" + E, ()),
], ids=[f"A13-{n:02}" for n in range(1, 24)])
def test_a13_text(catalog, content, expected):
    events = OfficialEventExtractor(catalog).extract((document(content),), as_of=CUT)
    assert tuple(event.category.value for event in events) == expected
    for event in events:
        assert event.description == content[event.content_start:event.content_end]


@pytest.mark.parametrize(("case", "expected", "error"), [
    (24, None, (ValueError, "cutoff")),
    (25, None, (ValueError, "cutoff")),
    (26, [2], None),
    (27, None, (ValueError, "timezone-aware")),
    (28, [1, 2], None),
    (29, None, (ValueError, "higher revision")),
    (30, [1], None),
    (31, None, (ValueError, "conflicting document identity")),
    (32, None, (KeyError, "unknown")),
    (33, None, (ValueError, "provenance")),
    (34, [1, 1], None),
], ids=[f"A13-{n:02}" for n in range(24, 35)])
def test_a13_contract(catalog, case, expected, error):
    a = document(M)
    b = replace(a, revision=2, received_at=CUT)
    bad = replace(a)
    object.__setattr__(bad, "content_sha256", "0" * 64)
    inputs = {
        24: ((document(M, published_at=CUT + timedelta(seconds=1),
                       received_at=CUT + timedelta(seconds=2)),), CUT),
        25: ((b,), T + timedelta(minutes=1)),
        26: ((b,), CUT),
        27: ((a,), CUT.replace(tzinfo=None)),
        28: ((b, a), CUT),
        29: ((replace(a, received_at=CUT), replace(b, received_at=a.received_at)), CUT),
        30: ((a, a), CUT),
        31: ((a, replace(a, title="Conflicting")), CUT),
        32: ((replace(a, source_id="unknown"),), CUT),
        33: ((bad,), CUT),
        34: ((a, replace(a, document_id="republication")), CUT),
    }
    docs, cutoff = inputs[case]
    extractor = OfficialEventExtractor(catalog)
    if error:
        kind, message = error
        with pytest.raises(kind, match=message):
            extractor.extract(docs, as_of=cutoff)
    else:
        events = extractor.extract(docs, as_of=cutoff)
        assert [e.revision for e in events] == expected
        assert len({e.event_id for e in events}) == len(events)


def test_a13_35_stateless_cross_call_conflict(catalog):
    a = document(M)
    extractor = OfficialEventExtractor(catalog)
    assert len(extractor.extract((a,), as_of=CUT)) == 1
    assert len(extractor.extract((replace(a, title="Conflicting"),), as_of=CUT)) == 1


def test_a13_36_ingestion_retains_conflict_history(catalog):
    a = document(M)
    service = OfficialIngestionService(catalog)
    payload = {key: getattr(a, key) for key in (
        "source_id", "document_id", "revision", "title", "content", "published_at", "received_at",
    )}
    service.ingest((payload,), as_of=CUT)
    with pytest.raises(ValueError, match="conflicting replay"):
        service.ingest((payload | {"title": "Conflicting"},), as_of=CUT)


@pytest.mark.parametrize("context", [
    "## Hipótese", "Simulação:", "Minuta futura:", "Projeção não realizada:",
    "O comunicado desmentiu a seguinte afirmação.",
    "O comunicado negou a afirmação abaixo.",
])
def test_context_ends_at_factual_section(catalog, context):
    content = f"{context}\r\n\r\n{M}\r\n\r\n## Fatos confirmados\r\n{I}"
    extractor = OfficialEventExtractor(catalog)
    event, = extractor.extract((document(content),), as_of=CUT)
    assert event.description == I
    assert event.content_start == content.index(I)


def test_segmented_evidence_replay_and_observational_contract(catalog):
    wrapped = M.replace("taxa Selic", "taxa\r\n  Selic")
    content = f"  {wrapped};  {I}"
    doc = document(content)
    extractor = OfficialEventExtractor(catalog)
    events = extractor.extract((doc,), as_of=CUT)
    assert len(events) == 2
    assert events == extractor.extract((doc, doc), as_of=CUT)
    assert [e.description for e in events] == [wrapped + ";", I]
    for event in events:
        assert event.description == content[event.content_start:event.content_end]
        assert event.content_sha256 == doc.content_sha256
        assert type(event) is ExtractedOfficialEvent and event.state is DocumentState.UNVERIFIED
        assert not any(hasattr(event, name) for name in ("action", "signal", "entry", "stop", "target"))
