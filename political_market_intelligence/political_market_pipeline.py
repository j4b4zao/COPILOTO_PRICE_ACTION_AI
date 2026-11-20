"""Offline composition of political evidence and delivered-market replay."""

from dataclasses import dataclass, field
from datetime import datetime

from .event_deduplicator import EventDeduplicator
from .event_model import EventCategory, EventRecord, FactStatus, _utc
from .market_impact_validator import (
    DeliveredMarketSample, MarketAssessment, MarketImpactValidator, MarketSession, MarketWindows, _asset,
)
from .political_sentiment_engine import (
    EconomicInterpretation, ImpactHypothesis, PoliticalSentimentEngine,
)
from .presidential_agenda_collector import (
    AgendaFixture, AgendaSnapshot, AgendaStatus, PresidentialAgendaCollector,
)
from .source_registry import SourceRegistry, SourceStatus
from .speech_monitor import SpeechFixture, SpeechMonitor, SpeechSnapshot


@dataclass(frozen=True, slots=True)
class MarketTarget:
    contract: str
    session: MarketSession
    windows: MarketWindows = MarketWindows()

    def __post_init__(self) -> None:
        _asset(self.contract)


@dataclass(frozen=True, slots=True)
class MarketReaction:
    hypothesis: ImpactHypothesis
    assessment: MarketAssessment
    market_evidence: tuple[DeliveredMarketSample, ...]
    concurrent_evidence: tuple[EventRecord, ...]


@dataclass(frozen=True, slots=True)
class SpeechAssessment:
    speech: SpeechFixture
    occurrences: tuple[EventRecord, ...]
    interpretation: EconomicInterpretation
    hypotheses: tuple[ImpactHypothesis, ...]
    reactions: tuple[MarketReaction, ...]
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PoliticalMarketReplay:
    as_of: datetime
    sources: tuple[tuple[str, SourceStatus], ...]
    agenda: AgendaSnapshot
    events: tuple[EventRecord, ...]
    event_conflicts: tuple[tuple[str, str, int], ...]
    speeches: SpeechSnapshot
    assessments: tuple[SpeechAssessment, ...]
    observational_only: bool = field(init=False, default=True)
    order_execution_allowed: bool = field(init=False, default=False)


def _occurrences(agenda: AgendaSnapshot, speech: SpeechFixture) -> tuple[EventRecord, ...]:
    if speech.associated_event_id in agenda.conflicts:
        return ()
    return tuple(
        fixture.record for fixture in agenda.current
        if fixture.event_id == speech.associated_event_id
        and fixture.status is AgendaStatus.OCCURRENCE_CONFIRMED
        and fixture.authority == speech.authority
        and fixture.occurred_at == speech.speech_at
    )


class PoliticalMarketPipeline:
    """Replay one deterministic evidence/market snapshot without operational callbacks."""

    def __init__(self, sources: SourceRegistry) -> None:
        self._sources = sources
        self._agenda = PresidentialAgendaCollector(sources)
        self._speech = SpeechMonitor(sources)
        self._sentiment = PoliticalSentimentEngine(self._speech)
        self._impact = MarketImpactValidator()

    def replay(
        self, *, agenda: tuple[AgendaFixture, ...], speeches: tuple[SpeechFixture, ...],
        market: tuple[DeliveredMarketSample, ...], targets: tuple[MarketTarget, ...],
        interpreted_at: datetime, hypothesized_at: datetime, as_of: datetime,
        event_sources: tuple[str, ...] = (),
    ) -> PoliticalMarketReplay:
        """Apply explicit replay cutoffs for each derived stage.

        The replay keeps earlier derivations for audit when later evidence
        invalidates them. Only still-current claims are assessed against market.
        """
        as_of = _utc(as_of, "as_of")
        interpreted_at = _utc(interpreted_at, "interpreted_at")
        hypothesized_at = _utc(hypothesized_at, "hypothesized_at")
        if hypothesized_at < interpreted_at:
            raise ValueError("hypothesized_at precedes interpreted_at")
        if type(market) is not tuple or any(type(sample) is not DeliveredMarketSample for sample in market):
            raise TypeError("replay requires delivered market projections")
        by_asset = {_asset(target.contract): target for target in targets}
        if len(by_asset) != len(targets):
            raise ValueError("replay requires at most one target contract per asset")

        source_ids = {fixture.source_id for fixture in (*agenda, *speeches)} | set(event_sources)
        sources = tuple((source_id, self._sources.get(source_id).status) for source_id in sorted(source_ids))
        final_agenda = self._agenda.collect(agenda, as_of=as_of)
        final_speech = self._speech.collect(speeches, as_of=as_of)

        events = EventDeduplicator()
        for fixture in final_agenda.current:
            if fixture.status is AgendaStatus.OCCURRENCE_CONFIRMED:
                events.ingest(fixture.record)
        for source_id in sorted(set(event_sources)):
            for record in self._sources.records_as_of(source_id, as_of):
                if record.category is EventCategory.CONFIRMED_FACT and record.fact_status is FactStatus.OCCURRED:
                    events.ingest(record)
        observed_events = events.history()
        event_conflicts = events.conflicts()
        latest = {record.key[:2]: record.revision for record in observed_events}
        current_events = tuple(record for record in observed_events if record.revision == latest[record.key[:2]])

        assessments = []
        if interpreted_at <= as_of:
            initial_agenda = self._agenda.collect(agenda, as_of=interpreted_at)
            initial_speech = self._speech.collect(speeches, as_of=interpreted_at)
            speech_by_record = {fixture.record: fixture for fixture in initial_speech.current}
            interpretations = self._sentiment.interpret(speeches, as_of=interpreted_at)

            hypothesis_agenda = self._agenda.collect(agenda, as_of=hypothesized_at) if hypothesized_at <= as_of else None
            hypothesis_speech = self._speech.collect(speeches, as_of=hypothesized_at) if hypothesized_at <= as_of else None
            for interpretation in interpretations:
                fixture = speech_by_record[interpretation.transcript]
                occurrences = _occurrences(initial_agenda, fixture)
                if not occurrences:
                    continue
                if hypothesis_speech is None:
                    assessments.append(SpeechAssessment(
                        fixture, occurrences, interpretation, (), (), "HYPOTHESIS_NOT_YET_AVAILABLE",
                    ))
                    continue
                if (interpretation.transcript not in hypothesis_speech.verified_records
                        or not _occurrences(hypothesis_agenda, fixture)):
                    assessments.append(SpeechAssessment(
                        fixture, occurrences, interpretation, (), (), "EVIDENCE_CHANGED_BEFORE_HYPOTHESIS",
                    ))
                    continue
                hypotheses = self._sentiment.hypothesize(
                    interpretation, fixtures=speeches, as_of=hypothesized_at,
                )
                if (interpretation.transcript not in final_speech.verified_records
                        or not _occurrences(final_agenda, fixture)):
                    assessments.append(SpeechAssessment(
                        fixture, occurrences, interpretation, hypotheses, (), "EVIDENCE_CHANGED_BEFORE_ASSESSMENT",
                    ))
                    continue

                concurrent = tuple(
                    record for record in current_events
                    if record.event_id != fixture.associated_event_id and record.event_time == fixture.speech_at
                )
                reactions = tuple(
                    self._assess(hypothesis, by_asset[hypothesis.asset], market, concurrent, as_of)
                    for hypothesis in hypotheses if hypothesis.asset in by_asset
                )
                assessments.append(SpeechAssessment(
                    fixture, occurrences, interpretation, hypotheses, reactions,
                    None if reactions else "MARKET_TARGET_NOT_CONFIGURED",
                ))
        return PoliticalMarketReplay(
            as_of, sources, final_agenda, observed_events, event_conflicts, final_speech, tuple(assessments),
        )

    def _assess(
        self, hypothesis: ImpactHypothesis, target: MarketTarget,
        market: tuple[DeliveredMarketSample, ...], concurrent: tuple[EventRecord, ...], as_of: datetime,
    ) -> MarketReaction:
        event = hypothesis.interpretation.transcript.event_time
        evidence = tuple(sorted(
            {sample for sample in market
             if sample.received_timestamp <= as_of and sample.asset is hypothesis.asset
             and event - target.windows.before <= sample.source_timestamp <= event + target.windows.after},
            key=lambda sample: (sample.source_timestamp, sample.received_timestamp, sample.contract, repr(sample)),
        ))
        assessment = self._impact.evaluate(
            hypothesis, evidence, contract=target.contract, session=target.session,
            as_of=as_of, windows=target.windows, concurrent_events=concurrent,
        )
        return MarketReaction(hypothesis, assessment, evidence, concurrent)

