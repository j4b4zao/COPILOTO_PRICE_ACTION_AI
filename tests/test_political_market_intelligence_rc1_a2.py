"""Offline contracts for PMI evidence, fixtures and revision history."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from political_market_intelligence import (
    DeduplicationResult,
    EventCategory,
    EventDeduplicator,
    EventRecord,
    EvidenceReference,
    FactStatus,
    SourceFixture,
    SourceRegistry,
    SourceStatus,
)


NOW = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)


@pytest.fixture
def fact():
    return EventRecord(
        source_id="agenda-fixture",
        event_id="pronunciamento-1",
        revision=1,
        category=EventCategory.CONFIRMED_FACT,
        provenance="fixture:agenda/1",
        content="Pronunciamento realizado",
        event_time=NOW - 3 * MINUTE,
        published_at=NOW - 2 * MINUTE,
        received_at=NOW - MINUTE,
        verified_at=NOW,
        evidence=[EvidenceReference("document-fixture", "nota-1", 1, NOW - MINUTE)],
        fact_status=FactStatus.OCCURRED,
    )


def test_evidence_is_immutable_and_detached_from_input(fact):
    references = list(fact.evidence)
    event = replace(fact, evidence=references)
    references.clear()
    assert event.evidence == fact.evidence
    with pytest.raises(FrozenInstanceError):
        event.content = "Alterado"
    with pytest.raises(FrozenInstanceError):
        event.evidence[0].event_id = "Outro"


def test_timezone_offsets_represent_the_same_revision(fact):
    local = timezone(timedelta(hours=-3))
    variant = replace(fact, published_at=fact.published_at.astimezone(local))
    assert variant == fact
    assert variant.published_at.tzinfo is timezone.utc


@pytest.mark.parametrize("field", ["event_time", "published_at", "received_at", "verified_at"])
def test_naive_event_timestamps_are_rejected(fact, field):
    with pytest.raises(ValueError, match=field):
        replace(fact, **{field: getattr(fact, field).replace(tzinfo=None)})


def test_naive_evidence_and_query_times_are_rejected(fact):
    naive = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match="available_at"):
        replace(fact.evidence[0], available_at=naive)
    with pytest.raises(ValueError, match="as_of"):
        fact.is_available_at(naive)


@pytest.mark.parametrize("field,value", [
    ("received_at", NOW - 4 * MINUTE),
    ("verified_at", NOW - 2 * MINUTE),
])
def test_rejects_inconsistent_publication_receipt_verification(fact, field, value):
    with pytest.raises(ValueError, match=field):
        replace(fact, **{field: value})


def test_late_verification_does_not_backdate_a_transcript(fact):
    transcript = replace(
        fact, event_id="transcricao-1", category=EventCategory.VERIFIED_TRANSCRIPT,
        fact_status=None, verified_at=NOW + MINUTE,
    )
    assert transcript.event_time < transcript.published_at < transcript.received_at
    assert transcript.received_at < transcript.verified_at == transcript.available_at
    assert not transcript.is_available_at(NOW)
    assert transcript.is_available_at(NOW + MINUTE)
    with pytest.raises(ValueError, match="verified_at"):
        replace(transcript, verified_at=None)


def test_evidence_delays_availability_and_must_exist_at_verification(fact):
    late = replace(fact.evidence[0], available_at=NOW + MINUTE)
    with pytest.raises(ValueError, match="verification"):
        replace(fact, evidence=(late,))
    interpretation = replace(
        fact, category=EventCategory.AI_INTERPRETATION, fact_status=None,
        verified_at=None, evidence=(late,),
    )
    assert not interpretation.is_available_at(NOW)
    assert interpretation.is_available_at(NOW + MINUTE)


@pytest.mark.parametrize("field,value", [
    ("source_id", " "), ("event_id", ""), ("revision", 0), ("revision", True),
])
def test_stable_key_requires_explicit_identity(fact, field, value):
    with pytest.raises(ValueError, match=field):
        replace(fact, **{field: value})


def test_fact_and_ai_interpretation_have_distinct_contracts(fact):
    interpretation = replace(
        fact, event_id="interpretacao-1", category=EventCategory.AI_INTERPRETATION,
        fact_status=None, verified_at=None,
    )
    assert interpretation.category is EventCategory.AI_INTERPRETATION
    with pytest.raises(ValueError, match="fact_status"):
        replace(interpretation, fact_status=FactStatus.OCCURRED)
    with pytest.raises(ValueError, match="verified_at"):
        replace(fact, verified_at=None)


def test_hypothesis_and_observation_have_distinct_contracts(fact):
    hypothesis = replace(
        fact, category=EventCategory.IMPACT_HYPOTHESIS, fact_status=None,
        verified_at=None, event_time=NOW + MINUTE, contract="WINZ26",
    )
    assert hypothesis.is_available_at(NOW)
    with pytest.raises(ValueError, match="cannot precede"):
        replace(hypothesis, category=EventCategory.OBSERVED_REACTION)
    observed = replace(
        hypothesis, category=EventCategory.OBSERVED_REACTION,
        event_time=fact.event_time, contract="WDOZ26",
    )
    assert observed.category is EventCategory.OBSERVED_REACTION
    for contract in (None, "WDO", "WINY26", "DOLZ26"):
        with pytest.raises(ValueError, match="contract"):
            replace(observed, contract=contract)


def test_agenda_does_not_confirm_future_occurrence(fact):
    agenda = replace(fact, event_time=NOW + MINUTE, fact_status=FactStatus.SCHEDULED)
    assert agenda.is_available_at(NOW)
    assert agenda.fact_status is FactStatus.SCHEDULED
    with pytest.raises(ValueError, match="cannot precede"):
        replace(agenda, fact_status=FactStatus.OCCURRED)
    occurred = replace(
        agenda, revision=2, fact_status=FactStatus.OCCURRED,
        published_at=NOW + MINUTE, received_at=NOW + 2 * MINUTE,
        verified_at=NOW + 3 * MINUTE,
    )
    assert not occurred.is_available_at(NOW + 2 * MINUTE)
    assert occurred.is_available_at(NOW + 3 * MINUTE)


def test_references_cannot_be_missing_duplicate_or_self_referential(fact):
    with pytest.raises(ValueError, match="at least one"):
        replace(fact, evidence=())
    with pytest.raises(ValueError, match="distinct"):
        replace(fact, evidence=fact.evidence * 2)
    with pytest.raises(ValueError, match="cannot reference"):
        replace(fact, evidence=(EvidenceReference(*fact.key, NOW),))


@pytest.mark.parametrize("status", [
    SourceStatus.UNAVAILABLE, SourceStatus.UNVERIFIED, SourceStatus.CONFLICTING,
])
def test_nonavailable_source_retains_fixture_for_audit_only(fact, status):
    fixture = SourceFixture(fact.source_id, {fact.category}, status, [fact])
    registry = SourceRegistry((fixture,))
    assert registry.get(fact.source_id).status is status
    assert registry.get(fact.source_id).records == (fact,)
    assert registry.records_as_of(fact.source_id, NOW) == ()


def test_available_source_filters_by_time_and_validates_capabilities(fact):
    records = [fact]
    capabilities = {fact.category}
    fixture = SourceFixture(fact.source_id, capabilities, SourceStatus.AVAILABLE, records)
    records.clear()
    capabilities.clear()
    registry = SourceRegistry((fixture,))
    assert registry.records_as_of(fact.source_id, NOW - MINUTE) == ()
    assert registry.records_as_of(fact.source_id, NOW) == (fact,)
    with pytest.raises(ValueError, match="capabilities"):
        replace(fixture, capabilities={EventCategory.AI_INTERPRETATION})
    with pytest.raises(ValueError, match="belong"):
        replace(fixture, source_id="another-fixture")
    with pytest.raises(ValueError, match="duplicate"):
        SourceRegistry((fixture, fixture))
    with pytest.raises(TypeError, match="SourceFixture"):
        SourceRegistry(("fixture.json",))


def test_revision_keeps_identifier_and_preserves_history(fact):
    correction = replace(fact, revision=2, content="Pronunciamento remarcado")
    assert correction.key[:2] == fact.key[:2]
    assert correction.key != fact.key
    dedup = EventDeduplicator()
    assert dedup.ingest(correction) is DeduplicationResult.ADDED
    assert dedup.ingest(fact) is DeduplicationResult.ADDED
    assert dedup.history() == (fact, correction)
    assert dedup.conflicts() == ()


def test_exact_repeat_and_equivalent_evidence_order_are_idempotent(fact):
    references = fact.evidence + (EvidenceReference("another-fixture", "note", 1, NOW),)
    event = replace(fact, evidence=references)
    repeated = replace(event, evidence=references[::-1])
    dedup = EventDeduplicator()
    assert dedup.ingest(event) is DeduplicationResult.ADDED
    before = dedup.history()
    assert dedup.ingest(repeated) is DeduplicationResult.DUPLICATE
    assert dedup.history() == before
    assert dedup.conflicts() == ()


def test_conflicts_keep_both_variants_and_other_sources(fact):
    conflicting = replace(fact, content="Conteudo divergente")
    another_source = replace(conflicting, source_id="another-fixture")
    dedup = EventDeduplicator()
    assert dedup.ingest(fact) is DeduplicationResult.ADDED
    assert dedup.ingest(conflicting) is DeduplicationResult.CONFLICT
    assert dedup.ingest(another_source) is DeduplicationResult.ADDED
    assert dedup.ingest(conflicting) is DeduplicationResult.DUPLICATE
    assert set(dedup.history()) == {fact, conflicting, another_source}
    assert dedup.conflicts() == (fact.key,)

    reversed_ingestion = EventDeduplicator()
    for event in (another_source, conflicting, fact):
        reversed_ingestion.ingest(event)
    assert reversed_ingestion.history() == dedup.history()
    assert reversed_ingestion.conflicts() == dedup.conflicts()

