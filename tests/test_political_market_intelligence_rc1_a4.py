"""Offline interpretation and hypothesis contracts for political speeches."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from political_market_intelligence import (
    EventCategory, EvidenceReference, SourceFixture, SourceRegistry, SourceStatus,
)
from political_market_intelligence.political_sentiment_engine import (
    EconomicInterpretation, EconomicTone, EconomicTopic, ImpactDirection, ImpactHypothesis,
    MarketAsset, PoliticalSentimentEngine, RULES_VERSION,
)
from political_market_intelligence.speech_monitor import SpeechFixture, SpeechMonitor, SpeechStatus


NOW = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)
POSITIVE = "A responsabilidade fiscal sustenta o controle de gastos."


def make_engine(status=SourceStatus.AVAILABLE):
    capabilities = {EventCategory.VERIFIED_TRANSCRIPT}
    sources = SourceRegistry((
        SourceFixture("principal", capabilities, status),
        SourceFixture("secundaria", capabilities, SourceStatus.AVAILABLE),
    ))
    return PoliticalSentimentEngine(SpeechMonitor(sources))


@pytest.fixture
def engine():
    return make_engine()


@pytest.fixture
def speech():
    return SpeechFixture(
        source_id="principal", event_id="transcricao-1", associated_event_id="discurso-1",
        revision=1, authority="Autoridade simulada", status=SpeechStatus.VERIFIED,
        speech_at=NOW - 3 * MINUTE, published_at=NOW - 2 * MINUTE,
        received_at=NOW - MINUTE, verified_at=NOW, provenance="fixture:discurso/1",
        evidence=(EvidenceReference("documento-fixture", "texto", 1, NOW - MINUTE),),
        text=POSITIVE,
    )


@pytest.mark.parametrize("text,topics,tone", [
    (POSITIVE, (EconomicTopic.FISCAL_POLICY, EconomicTopic.PUBLIC_SPENDING), EconomicTone.RISK_ON),
    ("Deterioração fiscal e aumento da dívida pública.",
     (EconomicTopic.FISCAL_POLICY, EconomicTopic.PUBLIC_DEBT), EconomicTone.RISK_OFF),
    ("A política monetária avalia a Selic, com inflação em queda.",
     (EconomicTopic.INFLATION, EconomicTopic.INTEREST_RATES), EconomicTone.RISK_ON),
    ("Talvez haja melhora fiscal, depende do cenário.",
     (EconomicTopic.FISCAL_POLICY,), EconomicTone.UNCERTAIN),
    ("Houve melhora fiscal, mas também aumento da dívida.",
     (EconomicTopic.FISCAL_POLICY, EconomicTopic.PUBLIC_DEBT), EconomicTone.MIXED),
    ("A cerimônia começa em instantes.", (), EconomicTone.NEUTRAL),
    ("Gastos públicos, dívida, câmbio, comércio exterior, intervenção estatal e incerteza política.",
     (EconomicTopic.PUBLIC_SPENDING, EconomicTopic.PUBLIC_DEBT, EconomicTopic.EXCHANGE_RATE,
      EconomicTopic.TRADE_POLICY, EconomicTopic.STATE_INTERVENTION,
      EconomicTopic.POLITICAL_UNCERTAINTY), EconomicTone.UNCERTAIN),
])
def test_economic_classification_keeps_literal_evidence(engine, speech, text, topics, tone):
    transcript = replace(speech, text=text)
    (result,) = engine.interpret((transcript,), as_of=NOW)
    assert result.category is EventCategory.AI_INTERPRETATION
    assert result.transcript is transcript.record
    assert (result.event_id, result.source_id, result.transcript_revision) == (
        transcript.event_id, transcript.source_id, transcript.revision,
    )
    assert result.topics == topics
    assert result.economic_tone is tone
    assert result.rules_version == RULES_VERSION
    assert 0 <= result.confidence <= 1
    assert result.evidence_refs[0].key == transcript.record.key
    assert result.evidence_refs[1:] == transcript.evidence
    assert all(excerpt in text for excerpt in result.supporting_excerpts)
    assert bool(result.supporting_excerpts) is bool(topics)


@pytest.mark.parametrize("status,text", [
    (SpeechStatus.PENDING, ""),
    (SpeechStatus.PARTIAL, "Deterioração fiscal. Alta para WDO."),
    (SpeechStatus.CONFLICTING, "Deterioração fiscal. Alta para WDO."),
])
def test_ineligible_workflow_transcripts_produce_no_interpretation(engine, speech, status, text):
    candidate = replace(speech, status=status, verified_at=None, text=text)
    assert engine.interpret((candidate,), as_of=NOW) == ()


@pytest.mark.parametrize("source_status", [
    SourceStatus.UNVERIFIED, SourceStatus.UNAVAILABLE, SourceStatus.CONFLICTING,
])
def test_ineligible_sources_produce_no_interpretation(speech, source_status):
    assert make_engine(source_status).interpret((speech,), as_of=NOW) == ()


def test_versioned_correction_and_late_conflict_use_replay_cutoff(engine, speech):
    correction = replace(
        speech, status=SpeechStatus.CORRECTED, revision=2,
        text="Deterioração fiscal.", published_at=NOW + MINUTE,
        received_at=NOW + 2 * MINUTE, verified_at=NOW + 3 * MINUTE,
    )
    earlier = engine.interpret((correction, speech), as_of=correction.received_at)[0]
    assert earlier.transcript_revision == 1
    assert earlier.economic_tone is EconomicTone.RISK_ON
    later = engine.interpret((speech, correction), as_of=correction.verified_at)[0]
    assert later.transcript_revision == 2
    assert later.economic_tone is EconomicTone.RISK_OFF
    assert earlier.transcript_revision == 1

    conflicting = replace(correction, source_id="secundaria", text="Melhora fiscal.")
    assert engine.interpret((speech, correction, conflicting), as_of=correction.verified_at) == ()
    with pytest.raises(ValueError, match="without conflicts"):
        engine.hypothesize(
            earlier, fixtures=(speech, correction, conflicting), as_of=correction.verified_at,
        )


def test_delayed_receipt_verification_and_interpretation_each_gate_replay(engine, speech):
    delayed = replace(speech, received_at=NOW + MINUTE, verified_at=NOW + 2 * MINUTE)
    for at in (delayed.published_at, delayed.received_at):
        assert engine.interpret((delayed,), as_of=at) == ()
    calculated = NOW + 3 * MINUTE
    (result,) = engine.interpret((delayed,), as_of=calculated)
    assert result.available_at == calculated
    assert not result.is_available_at(delayed.verified_at)
    assert result.is_available_at(calculated)
    with pytest.raises(ValueError, match="cannot precede its interpretation"):
        engine.hypothesize(result, fixtures=(delayed,), as_of=delayed.verified_at)
    released = calculated + MINUTE
    for hypothesis in engine.hypothesize(result, fixtures=(delayed,), as_of=released):
        assert hypothesis.available_at == released
        assert not hypothesis.is_available_at(calculated)
    with pytest.raises(ValueError, match="timezone-aware"):
        engine.interpret((delayed,), as_of=calculated.replace(tzinfo=None))


def test_interpretation_requires_verified_evidence_and_actual_excerpts(engine, speech):
    with pytest.raises(ValueError, match="evidence"):
        replace(speech, evidence=())
    with pytest.raises(ValueError, match="verified transcript with evidence"):
        EconomicInterpretation(transcript=None, available_at=NOW)
    with pytest.raises(ValueError, match="cannot precede"):
        EconomicInterpretation(transcript=speech.record, available_at=NOW - MINUTE)
    (interpretation,) = engine.interpret((speech,), as_of=NOW)
    with pytest.raises(ValueError, match="supporting_excerpts"):
        replace(interpretation, supporting_excerpts=("Trecho inexistente",))
    with pytest.raises(ValueError, match="economic interpretation"):
        engine.hypothesize(None, fixtures=(speech,), as_of=NOW)
    with pytest.raises(ValueError, match="economic interpretation"):
        ImpactHypothesis(interpretation=None, asset=MarketAsset.WIN, available_at=NOW)


@pytest.mark.parametrize("text,wins,wdo", [
    ("Melhora fiscal. Alta para WIN.", ImpactDirection.UP, ImpactDirection.UNCERTAIN),
    ("Melhora fiscal. Alta para WIN e alta para WDO.", ImpactDirection.UP, ImpactDirection.UP),
    ("Deterioração fiscal. Queda para WIN e alta para WDO.", ImpactDirection.DOWN, ImpactDirection.UP),
    ("Deterioração fiscal.", ImpactDirection.UNCERTAIN, ImpactDirection.UNCERTAIN),
    ("Pode haver melhora fiscal e alta para WIN.", ImpactDirection.UNCERTAIN, ImpactDirection.UNCERTAIN),
    ("Melhora fiscal. Alta para WIN e queda para WIN.", ImpactDirection.UNCERTAIN, ImpactDirection.UNCERTAIN),
    ("Melhora fiscal. Alta para WIN?", ImpactDirection.UNCERTAIN, ImpactDirection.UNCERTAIN),
    ("A cerimônia começou.", ImpactDirection.NEUTRAL, ImpactDirection.NEUTRAL),
])
def test_hypotheses_are_independent_observational_and_deterministic(engine, speech, text, wins, wdo):
    transcript = replace(speech, text=text)
    (interpretation,) = engine.interpret((transcript,), as_of=NOW)
    assert engine.interpret((transcript, transcript), as_of=NOW) == (interpretation,)
    hypotheses = engine.hypothesize(interpretation, fixtures=(transcript,), as_of=NOW)
    assert hypotheses == engine.hypothesize(interpretation, fixtures=(transcript,), as_of=NOW)
    win, dollar = hypotheses
    assert (win.asset, dollar.asset) == (MarketAsset.WIN, MarketAsset.WDO)
    assert (win.direction, dollar.direction) == (wins, wdo)
    for hypothesis in hypotheses:
        assert hypothesis.interpretation is interpretation
        assert hypothesis.category is EventCategory.IMPACT_HYPOTHESIS
        assert hypothesis.observational_only
        assert not hypothesis.order_execution_allowed
        assert not hasattr(hypothesis, "signal")
        assert all(excerpt in text for excerpt in hypothesis.supporting_excerpts)
    with pytest.raises(FrozenInstanceError):
        win.direction = ImpactDirection.UP

