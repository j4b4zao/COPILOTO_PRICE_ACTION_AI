"""Offline replay tests for agenda notices and simulated transcripts."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from political_market_intelligence import (
    EventCategory, EvidenceReference, FactStatus, SourceFixture, SourceRegistry, SourceStatus,
)
from political_market_intelligence.presidential_agenda_collector import (
    AgendaFixture, AgendaStatus, PresidentialAgendaCollector,
)
from political_market_intelligence.speech_monitor import SpeechFixture, SpeechMonitor, SpeechStatus


NOW = datetime(2026, 11, 20, 12, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)
EVIDENCE = (EvidenceReference("document-fixture", "notice", 1, NOW),)


def registry(status=SourceStatus.AVAILABLE):
    capabilities = {EventCategory.CONFIRMED_FACT, EventCategory.VERIFIED_TRANSCRIPT}
    return SourceRegistry((
        SourceFixture("official-fixture", capabilities, status),
        SourceFixture("secondary-fixture", capabilities, SourceStatus.AVAILABLE),
    ))


@pytest.fixture
def agenda():
    return AgendaFixture(
        source_id="official-fixture", event_id="speech-1", revision=1,
        authority="Autoridade simulada", office="Presidencia", title="Pronunciamento",
        location="Sala simulada", status=AgendaStatus.SCHEDULED,
        scheduled_at=NOW + 30 * MINUTE, published_at=NOW - MINUTE,
        received_at=NOW, verified_at=NOW, provenance="fixture:agenda/1", evidence=EVIDENCE,
    )


@pytest.fixture
def speech():
    return SpeechFixture(
        source_id="official-fixture", event_id="transcript-1", associated_event_id="speech-1",
        revision=1, authority="Autoridade simulada", status=SpeechStatus.PENDING,
        speech_at=NOW - MINUTE, published_at=NOW, received_at=NOW,
        provenance="fixture:speech/1",
    )


def revise_agenda(agenda, revision, delay, **updates):
    visible = NOW + delay * MINUTE
    return replace(
        agenda, revision=revision, published_at=visible - MINUTE,
        received_at=visible, verified_at=visible, **updates,
    )


def revise_speech(speech, revision=3, delay=3, **updates):
    visible = NOW + delay * MINUTE
    return replace(
        speech, revision=revision, published_at=NOW + MINUTE,
        received_at=visible - MINUTE, verified_at=visible,
        evidence=EVIDENCE, **updates,
    )


def test_initial_agenda_is_a_schedule(agenda):
    collector = PresidentialAgendaCollector(registry())
    assert collector.collect((agenda,), as_of=NOW - MINUTE).current == ()
    snapshot = collector.collect((agenda,), as_of=NOW)
    assert snapshot.current == snapshot.history == (agenda,)
    assert agenda.record.category is EventCategory.CONFIRMED_FACT
    assert agenda.record.fact_status is FactStatus.SCHEDULED
    assert agenda.occurred_at is None
    assert agenda.record.event_time == agenda.scheduled_at
    assert agenda.location == "Sala simulada"
    with pytest.raises(FrozenInstanceError):
        agenda.title = "Alterado"


def test_late_reschedule_preserves_previous_replay(agenda):
    updated = revise_agenda(
        agenda, 2, 11, status=AgendaStatus.RESCHEDULED, scheduled_at=NOW + 60 * MINUTE
    )
    collector = PresidentialAgendaCollector(registry())
    assert collector.collect((updated, agenda), as_of=updated.published_at).current == (agenda,)
    result = collector.collect((updated, agenda, updated), as_of=updated.received_at)
    assert result.history == (agenda, updated)
    assert result.current == (updated,)
    assert result.conflicts == ()
    assert result == collector.collect((agenda, updated), as_of=updated.received_at)


def test_cancelled_agenda_preserves_history_without_confirming_occurrence(agenda):
    cancelled = revise_agenda(agenda, 2, 5, status=AgendaStatus.CANCELLED, location=None)
    collector = PresidentialAgendaCollector(registry())
    snapshot = collector.collect((agenda, cancelled), as_of=cancelled.verified_at)
    assert snapshot.history == (agenda, cancelled)
    assert snapshot.current == (cancelled,)
    assert cancelled.record.fact_status is FactStatus.SCHEDULED
    assert cancelled.occurred_at is None
    with pytest.raises(ValueError, match="occurred_at"):
        replace(cancelled, occurred_at=NOW)


def test_confirmation_distinguishes_scheduled_and_actual_time(agenda):
    actual = agenda.scheduled_at + MINUTE
    confirmed = revise_agenda(
        agenda, 2, 33, status=AgendaStatus.OCCURRENCE_CONFIRMED, occurred_at=actual
    )
    collector = PresidentialAgendaCollector(registry())
    assert collector.collect((confirmed, agenda), as_of=actual).current == (agenda,)
    assert collector.collect((confirmed, agenda), as_of=confirmed.verified_at).current == (confirmed,)
    assert confirmed.record.fact_status is FactStatus.OCCURRED
    assert confirmed.record.event_time == actual
    assert confirmed.scheduled_at == agenda.scheduled_at
    with pytest.raises(ValueError, match="cannot precede"):
        replace(confirmed, occurred_at=confirmed.verified_at + MINUTE)


def test_agenda_conflicts_leave_both_sources_and_same_revision_visible(agenda):
    alternate = replace(
        agenda, source_id="secondary-fixture", status=AgendaStatus.CANCELLED,
        received_at=NOW + MINUTE, verified_at=NOW + MINUTE,
    )
    another_location = replace(agenda, location="Outro local")
    collector = PresidentialAgendaCollector(registry())
    assert collector.collect((alternate, agenda), as_of=NOW).conflicts == ()
    at = alternate.verified_at
    result = collector.collect((alternate, agenda, another_location, agenda), as_of=at)
    assert result.conflicts == ("speech-1",)
    assert set(result.history) == set(result.current) == {agenda, alternate, another_location}
    assert collector.collect((another_location, alternate, agenda), as_of=at) == result


def test_pending_and_partial_are_workflow_only(speech):
    partial = replace(
        speech, revision=2, status=SpeechStatus.PARTIAL, text="Trecho simulado",
        received_at=NOW + MINUTE,
    )
    monitor = SpeechMonitor(registry())
    first = monitor.collect((partial, speech, speech), as_of=NOW)
    assert first.history == first.current == (speech,)
    assert first.verified_records == ()
    result = monitor.collect((partial, speech), as_of=partial.received_at)
    assert result.history == (speech, partial)
    assert result.current == (partial,)
    assert result.verified_records == ()
    with pytest.raises(ValueError, match="verified_at"):
        replace(partial, verified_at=NOW + MINUTE)


def test_delayed_transcript_is_visible_only_after_receipt_and_verification(speech):
    verified = revise_speech(speech, delay=11, status=SpeechStatus.VERIFIED, text="Texto")
    monitor = SpeechMonitor(registry())
    for at in (verified.published_at, verified.received_at):
        snapshot = monitor.collect((verified, speech), as_of=at)
        assert snapshot.current == (speech,)
        assert snapshot.verified_records == ()
    result = monitor.collect((speech, verified), as_of=verified.verified_at)
    assert result.current == (verified,)
    assert result.verified_records == (verified.record,)
    assert verified.record.category is EventCategory.VERIFIED_TRANSCRIPT
    assert verified.record.content == verified.text
    assert verified.record.event_time == verified.speech_at
    with pytest.raises(ValueError, match="verified_at"):
        replace(verified, verified_at=None)


def test_verified_correction_keeps_original_revision(speech):
    verified = revise_speech(speech, status=SpeechStatus.VERIFIED, text="Original")
    corrected = revise_speech(
        speech, revision=4, delay=9, status=SpeechStatus.CORRECTED, text="Corrigido"
    )
    monitor = SpeechMonitor(registry())
    items = (corrected, verified, speech, corrected)
    assert monitor.collect(items, as_of=corrected.received_at).verified_records == (verified.record,)
    result = monitor.collect(items, as_of=corrected.verified_at)
    assert result.history == (speech, verified, corrected)
    assert result.current == (corrected,)
    assert result.verified_records == (corrected.record,)
    assert result.conflicts == ()
    with pytest.raises(ValueError, match="revision"):
        replace(corrected, revision=1)


def test_disagreeing_transcripts_are_retained_without_choosing_a_winner(speech):
    verified = revise_speech(speech, status=SpeechStatus.VERIFIED, text="Versao A")
    other = replace(verified, source_id="secondary-fixture", text="Versao B")
    collision = replace(verified, text="Versao A divergente")
    monitor = SpeechMonitor(registry())
    for divergent in (other, collision):
        result = monitor.collect((divergent, verified, verified), as_of=verified.verified_at)
        assert set(result.history) == set(result.current) == {verified, divergent}
        assert result.conflicts == ("speech-1",)
        assert result.verified_records == ()
        assert monitor.collect((verified, divergent), as_of=verified.verified_at) == result


def test_explicit_conflicting_transcript_remains_audit_evidence(speech):
    conflicting = replace(speech, status=SpeechStatus.CONFLICTING, text="Texto contestado")
    result = SpeechMonitor(registry()).collect((conflicting,), as_of=NOW)
    assert result.history == result.current == (conflicting,)
    assert result.conflicts == ("speech-1",)
    assert result.verified_records == ()


@pytest.mark.parametrize("status", [SourceStatus.UNAVAILABLE, SourceStatus.UNVERIFIED])
def test_disabled_source_produces_no_replay_records(agenda, speech, status):
    sources = registry(status)
    assert PresidentialAgendaCollector(sources).collect((agenda,), as_of=NOW).history == ()
    assert SpeechMonitor(sources).collect((speech,), as_of=NOW).history == ()
    assert sources.get(agenda.source_id).status is status


def test_registry_conflict_remains_identified_in_both_replays(agenda, speech):
    sources = registry(SourceStatus.CONFLICTING)
    agenda_result = PresidentialAgendaCollector(sources).collect((agenda,), as_of=NOW)
    assert agenda_result.history == (agenda,)
    assert agenda_result.conflicts == ("speech-1",)
    verified = revise_speech(speech, status=SpeechStatus.VERIFIED, text="Texto")
    speech_result = SpeechMonitor(sources).collect((verified,), as_of=verified.verified_at)
    assert speech_result.history == (verified,)
    assert speech_result.verified_records == ()
    assert speech_result.conflicts == ("speech-1",)


def test_replays_require_explicit_timezones(agenda, speech):
    naive = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match="scheduled_at"):
        replace(agenda, scheduled_at=naive)
    with pytest.raises(ValueError, match="speech_at"):
        replace(speech, speech_at=naive)
    with pytest.raises(ValueError, match="as_of"):
        PresidentialAgendaCollector(registry()).collect((agenda,), as_of=naive)
    with pytest.raises(ValueError, match="as_of"):
        SpeechMonitor(registry()).collect((speech,), as_of=naive)

