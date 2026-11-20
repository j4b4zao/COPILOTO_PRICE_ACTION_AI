"""Integrated offline PMI replay and operational isolation tests."""

from copy import deepcopy
from dataclasses import replace
from datetime import timedelta

import pytest

from political_market_intelligence import (
    EventCategory, EvidenceReference, SourceFixture, SourceRegistry, SourceStatus,
)
from political_market_intelligence.market_impact_validator import (
    Continuity, ImpactResult, MarketSession, MarketWindows, OfflineMarketReplay,
)
from political_market_intelligence.political_market_pipeline import MarketTarget, PoliticalMarketPipeline
from political_market_intelligence.political_sentiment_engine import EconomicTone, ImpactDirection, MarketAsset
from political_market_intelligence.presidential_agenda_collector import AgendaFixture, AgendaStatus
from political_market_intelligence.speech_monitor import SpeechFixture, SpeechStatus
from tests.test_pipeline_rc917_freshness_adversarial import offline_chain, protected_chain
from tests.test_pipeline_rc918_integrated_offline import make_collector
from tests.test_pipeline_rc920_integrated_offline import assert_publication, install_rtd
from tests.test_pipeline_rc920_source_recovery_adversarial import quote
from tests.test_political_market_intelligence_rc1_a5 import SESSION, at, market


CAPABILITIES = {EventCategory.CONFIRMED_FACT, EventCategory.VERIFIED_TRANSCRIPT}
TARGETS = (MarketTarget("WINZ26", SESSION), MarketTarget("WDOZ26", SESSION))


def setup_pipeline(source_status=SourceStatus.AVAILABLE, *, external_events=()):
    return PoliticalMarketPipeline(SourceRegistry((
        SourceFixture("principal", CAPABILITIES, source_status),
        SourceFixture("secondary", CAPABILITIES, SourceStatus.AVAILABLE),
        SourceFixture("calendar", {EventCategory.CONFIRMED_FACT}, SourceStatus.AVAILABLE, external_events),
    )))


def fixtures(event_at):
    evidence = (EvidenceReference("local-document", "document-1", 1, event_at - timedelta(minutes=4)),)
    scheduled = AgendaFixture(
        source_id="principal", event_id="event-1", revision=1, authority="Autoridade simulada",
        office="Presidencia", title="Pronunciamento", location="Sala simulada",
        status=AgendaStatus.SCHEDULED, scheduled_at=event_at - timedelta(minutes=1),
        published_at=event_at - timedelta(minutes=3), received_at=event_at - timedelta(minutes=3),
        verified_at=event_at - timedelta(minutes=3), provenance="fixture:agenda", evidence=evidence,
    )
    rescheduled = replace(
        scheduled, revision=2, status=AgendaStatus.RESCHEDULED, scheduled_at=event_at,
        published_at=event_at - timedelta(minutes=2), received_at=event_at - timedelta(minutes=2),
        verified_at=event_at - timedelta(minutes=2),
    )
    occurred = replace(
        rescheduled, revision=3, status=AgendaStatus.OCCURRENCE_CONFIRMED, occurred_at=event_at,
        published_at=event_at, received_at=event_at, verified_at=event_at,
    )
    partial = SpeechFixture(
        source_id="principal", event_id="transcript-1", associated_event_id="event-1",
        revision=1, authority=occurred.authority, status=SpeechStatus.PARTIAL,
        speech_at=event_at, published_at=event_at, received_at=event_at + timedelta(seconds=1),
        provenance="fixture:transcript", evidence=evidence, text="Melhora fiscal.",
    )
    verified = replace(
        partial, revision=2, status=SpeechStatus.VERIFIED,
        verified_at=event_at + timedelta(seconds=3),
        text="Melhora fiscal. Alta para WIN e alta para WDO.",
    )
    return (scheduled, rescheduled, occurred), (partial, verified)


def replay(*, pipeline=None, source_agenda=None, source_speeches=None, samples=(), targets=TARGETS,
           interpreted=4, hypothesized=5, cutoff=60, event_sources=()):
    default_agenda, default_speeches = fixtures(at(0))
    return (pipeline or setup_pipeline()).replay(
        agenda=default_agenda if source_agenda is None else source_agenda,
        speeches=default_speeches if source_speeches is None else source_speeches,
        market=samples, targets=targets, interpreted_at=at(interpreted),
        hypothesized_at=at(hypothesized), as_of=at(cutoff), event_sources=event_sources,
    )


def test_replay_carries_provenance_and_keeps_win_wdo_separate():
    win = market()
    wdo = market(contract="WDOZ26", prices=(104, 104, 104, 102, 101, 100), reverse_flow=True)
    source_agenda, source_speeches = fixtures(at(0))
    result = replay(samples=(*win, *wdo), source_agenda=source_agenda[::-1],
                    source_speeches=(*source_speeches, source_speeches[-1]))
    assert result == replay(samples=(*wdo[::-1], *win[::-1]))
    assert result.agenda.history == source_agenda
    assert result.events == (source_agenda[-1].record,)
    assert result.speeches.history == source_speeches
    (output,) = result.assessments
    assert output.occurrences == result.events
    assert output.speech == source_speeches[-1]
    assert output.interpretation.transcript == output.speech.record
    assert output.interpretation.evidence_refs[0].key == output.speech.record.key
    assert output.interpretation.available_at == at(4)
    assert [item.available_at for item in output.hypotheses] == [at(5), at(5)]
    assert [item.asset for item in output.hypotheses] == [MarketAsset.WIN, MarketAsset.WDO]
    assert [item.assessment.result for item in output.reactions] == [
        ImpactResult.COMPATIBLE, ImpactResult.DIVERGENT,
    ]
    for reaction, hypothesis, inputs in zip(output.reactions, output.hypotheses, (win, wdo), strict=True):
        assert reaction.hypothesis is hypothesis
        assert reaction.market_evidence == inputs
        assert reaction.assessment.evaluated_at == at(60)
        assert reaction.assessment.timing.event_time == at(0)
    assert result.observational_only and not result.order_execution_allowed


def test_reschedule_and_partial_transcript_are_visible_before_confirmation_and_verification():
    scheduled = replay(cutoff=-150)
    assert scheduled.agenda.current[0].status is AgendaStatus.SCHEDULED
    rescheduled = replay(cutoff=-60)
    assert rescheduled.agenda.current[0].status is AgendaStatus.RESCHEDULED
    assert rescheduled.events == rescheduled.speeches.history == rescheduled.assessments == ()
    partial = replay(cutoff=2)
    assert partial.agenda.current[0].status is AgendaStatus.OCCURRENCE_CONFIRMED
    assert partial.speeches.current[0].status is SpeechStatus.PARTIAL
    assert partial.assessments == ()
    verified = replay(cutoff=4)
    (output,) = verified.assessments
    assert output.speech.status is SpeechStatus.VERIFIED
    assert output.hypotheses == output.reactions == ()
    assert output.reason == "HYPOTHESIS_NOT_YET_AVAILABLE"


def test_cancelled_event_does_not_enter_interpretation_even_with_a_transcript():
    agenda, speeches = fixtures(at(0))
    cancelled = replace(agenda[-1], status=AgendaStatus.CANCELLED, occurred_at=None)
    result = replay(source_agenda=(*agenda[:-1], cancelled), source_speeches=speeches)
    assert result.agenda.current == (cancelled,)
    assert result.events == result.assessments == ()
    assert result.speeches.verified_records == (speeches[-1].record,)


def test_late_correction_invalidates_old_derivation_for_market_assessment():
    _, speeches = fixtures(at(0))
    corrected = replace(
        speeches[-1], revision=3, status=SpeechStatus.CORRECTED, text="Descontrole fiscal.",
        published_at=at(6), received_at=at(7), verified_at=at(8),
    )
    revisions = (*speeches, corrected)
    early = replay(source_speeches=revisions, cutoff=7)
    assert early.speeches.current == (speeches[-1],)
    stale = replay(source_speeches=revisions, samples=market()).assessments[0]
    assert stale.interpretation.transcript_revision == 2
    assert stale.hypotheses and not stale.reactions
    assert stale.reason == "EVIDENCE_CHANGED_BEFORE_ASSESSMENT"
    before_hypothesis = replay(source_speeches=revisions, hypothesized=9).assessments[0]
    assert before_hypothesis.reason == "EVIDENCE_CHANGED_BEFORE_HYPOTHESIS"
    assert before_hypothesis.hypotheses == ()
    current = replay(source_speeches=revisions, interpreted=9, hypothesized=10, samples=market())
    assert current.speeches.history == revisions
    assert current.assessments[0].interpretation.transcript_revision == 3


def test_ambiguous_speech_stays_uncertain_despite_directional_market_movement():
    _, speeches = fixtures(at(0))
    ambiguous = replace(speeches[-1], text="Talvez haja melhora fiscal e alta para WIN.")
    output = replay(source_speeches=(ambiguous,), samples=market()).assessments[0]
    assert output.interpretation.economic_tone is EconomicTone.UNCERTAIN
    assert {item.direction for item in output.hypotheses} == {ImpactDirection.UNCERTAIN}
    assert output.reactions[0].assessment.reasons == ("HYPOTHESIS_UNCERTAIN",)


@pytest.mark.parametrize("status", [SourceStatus.UNAVAILABLE, SourceStatus.CONFLICTING])
def test_source_status_is_visible_without_promoting_conflict_or_unavailability(status):
    result = replay(pipeline=setup_pipeline(status), samples=market())
    assert result.sources == (("principal", status),)
    assert result.assessments == ()
    if status is SourceStatus.CONFLICTING:
        assert result.agenda.conflicts == result.speeches.conflicts == ("event-1",)
    else:
        assert result.agenda.history == result.speeches.history == ()


def test_disagreement_between_sources_preserves_both_alternatives():
    agenda, speeches = fixtures(at(0))
    dispute = replace(speeches[-1], source_id="secondary", text="Deterioracao fiscal.")
    result = replay(source_agenda=agenda, source_speeches=(*speeches, dispute))
    assert set(result.speeches.current) == {speeches[-1], dispute}
    assert result.speeches.conflicts == ("event-1",)
    assert result.assessments == ()


def test_late_transcript_does_not_leak_and_cannot_validate_previous_movement():
    _, speeches = fixtures(at(0))
    late = replace(speeches[-1], received_at=at(70), verified_at=at(71))
    early = replay(source_speeches=(speeches[0], late), interpreted=72, hypothesized=73)
    assert early.speeches.history == (speeches[0],)
    assert early.assessments == ()
    later = replay(source_speeches=(speeches[0], late), interpreted=72, hypothesized=73,
                   cutoff=75, samples=market())
    reaction = later.assessments[0].reactions[0].assessment
    assert reaction.reasons == ("HYPOTHESIS_AFTER_EVENT_WINDOW",)
    assert reaction.price_final is None


@pytest.mark.parametrize("case,reason", [
    ("rollover", "ROLLOVER_OR_MULTIPLE_CONTRACTS"),
    ("closed_session", "OUTSIDE_SESSION"),
    ("gap", "MARKET_CONTINUITY_GAP"),
    ("missing_flow", "ORDER_FLOW_UNAVAILABLE_OR_REBASED"),
    ("contradictory_flow", "ORDER_FLOW_CONTRADICTS_PRICE"),
])
def test_market_adversities_remain_inconclusive(case, reason):
    samples = market()
    target = TARGETS[0]
    if case == "rollover":
        samples = (*samples[:3], *market(contract="WING27")[3:])
    elif case == "closed_session":
        target = MarketTarget("WINZ26", MarketSession(at(-300), at(-100)))
    elif case == "gap":
        samples = (*samples[:2], replace(samples[2], continuity=Continuity.GAP), *samples[3:])
    elif case == "missing_flow":
        samples = (*samples[:-1], replace(samples[-1], order_flow=None))
    else:
        samples = market(reverse_flow=True)
    reaction = replay(samples=samples, targets=(target,)).assessments[0].reactions[0]
    assert reaction.assessment.result is ImpactResult.INCONCLUSIVE
    assert reaction.assessment.reasons == (reason,)


def test_simultaneous_event_source_is_deduplicated_and_respects_cutoff():
    agenda, _ = fixtures(at(0))
    macro = replace(agenda[-1].record, source_id="calendar", event_id="monetary-1")
    future = replace(macro, event_id="late", received_at=at(61), verified_at=at(62))
    pipeline = setup_pipeline(external_events=(macro, future, macro))
    result = replay(pipeline=pipeline, samples=market(), event_sources=("calendar", "calendar"))
    assert set(result.events) == {agenda[-1].record, macro}
    reaction = result.assessments[0].reactions[0]
    assert reaction.concurrent_evidence == (macro,)
    assert reaction.assessment.reasons == ("SIMULTANEOUS_EVENTS",)

    corrected = replace(
        macro, revision=macro.revision + 1, event_time=at(10), published_at=at(10),
        received_at=at(11), verified_at=at(12),
    )
    updated = replay(pipeline=setup_pipeline(external_events=(macro, corrected)),
                     samples=market(), event_sources=("calendar",))
    assert {macro, corrected} <= set(updated.events)
    reaction = updated.assessments[0].reactions[0]
    assert reaction.concurrent_evidence == ()
    assert reaction.assessment.result is ImpactResult.COMPATIBLE


def test_future_market_delivery_is_excluded_from_reaction_evidence():
    samples = market()
    late = replace(samples[-1], received_timestamp=at(61))
    result = replay(samples=(*samples[:-1], late)).assessments[0].reactions[0]
    assert result.market_evidence == samples[:-1]
    assert result.assessment.final_at == at(30)


def test_failed_get_data_never_becomes_delivered_market_evidence(monkeypatch, protected_chain):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    adapter = OfflineMarketReplay()
    workbook.publish(quote(clock))
    marker = RuntimeError("after acceptance and before return")

    def fail_before_return(_reason):
        raise marker

    with monkeypatch.context() as patch:
        patch.setattr(type(collector), "_report_protected_acceptance", staticmethod(fail_before_return))
        with pytest.raises(RuntimeError) as raised:
            adapter.capture_next(collector.get_data)
        assert raised.value is marker
    workbook.publish(quote(clock))
    assert adapter.capture_next(collector.get_data) is None
    reaction = replay().assessments[0].reactions[0]
    assert reaction.market_evidence == ()
    assert reaction.assessment.reasons == ("NO_MARKET_DATA",)


def test_operational_results_are_exactly_equal_with_pmi_consumer(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    replica = deepcopy(pipeline)
    replica.temporal_reference_provider = clock.now
    start = clock.current
    event_time = start + timedelta(seconds=30)
    agenda, speeches = fixtures(event_time)
    validator = setup_pipeline()
    adapter = OfflineMarketReplay()
    sampled = []
    output_fields = ("strategy", "score", "risk", "decision", "alert")

    def run(operational_pipeline, enabled):
        workbook, collector = make_collector(monkeypatch, clock)
        rtd = install_rtd(collector, clock)
        read = rtd.reader.read_times_trades.side_effect
        trades = []

        def overlapping_quotes(symbol):
            payload = read(symbol)
            trades.insert(0, payload["trades"][0])
            return {**payload, "trades": list(trades)}

        rtd.reader.read_times_trades.side_effect = overlapping_quotes
        target = MarketTarget(
            "WINZ26", MarketSession(start - timedelta(seconds=30), start + timedelta(minutes=3)),
            MarketWindows(lateral_band_pct=0.01),
        )
        results = []
        for seconds, quote_price in ((0, 180_000), (30, 180_020), (45, 180_040), (60, 180_060), (90, 180_080)):
            clock.current = start + timedelta(seconds=seconds)
            workbook.publish(quote(clock, price=quote_price, volume=1000 + seconds))
            if enabled:
                delivered = []

                def receive():
                    context = collector.get_data()
                    delivered.append(context)
                    return context

                sampled.append(adapter.capture_next(receive))
                context = delivered[0]
                pmi = validator.replay(
                    agenda=agenda, speeches=speeches, market=tuple(sampled),
                    targets=(target,),
                    interpreted_at=event_time + timedelta(seconds=4),
                    hypothesized_at=event_time + timedelta(seconds=5),
                    as_of=clock.current,
                )
            else:
                context = collector.get_data()
            assert_publication(operational_pipeline, context, clock, capsys)
            results.append(deepcopy(tuple(getattr(context, name) for name in output_fields)))
        if enabled:
            (reaction,) = pmi.assessments[0].reactions
            assert reaction.market_evidence == tuple(sampled)
            assert reaction.assessment.result is ImpactResult.COMPATIBLE
        return results

    assert run(pipeline, False) == run(replica, True)

