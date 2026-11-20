"""Offline adverse cases for the PMI market impact replay."""

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from core.analysis_context import AnalysisContext
from core.market_state import MarketState
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState
from political_market_intelligence import (
    EventCategory, EventRecord, EvidenceReference, FactStatus,
    SourceFixture, SourceRegistry, SourceStatus,
)
from political_market_intelligence.market_impact_validator import (
    Continuity, ImpactResult, MarketImpactValidator, MarketSession, MarketWindows,
    OfflineMarketReplay, SampleQuality,
)
from political_market_intelligence.political_sentiment_engine import (
    ImpactDirection, PoliticalSentimentEngine,
)
from political_market_intelligence.speech_monitor import SpeechFixture, SpeechMonitor, SpeechStatus
from tests.test_pipeline_rc917_freshness_adversarial import offline_chain, protected_chain
from tests.test_pipeline_rc918_integrated_offline import make_collector
from tests.test_pipeline_rc920_source_recovery_adversarial import quote


EVENT = datetime(2026, 11, 20, 15, tzinfo=timezone.utc)
SESSION = MarketSession(EVENT - timedelta(hours=1), EVENT + timedelta(hours=1))
REPLAY = OfflineMarketReplay()
VALIDATOR = MarketImpactValidator()


def at(seconds):
    return EVENT + timedelta(seconds=seconds)


def hypothesis(*, asset="WIN", text=None, received=2, verified=3, interpreted=4, created=5):
    source = SourceFixture(
        "fixture", {EventCategory.VERIFIED_TRANSCRIPT}, SourceStatus.AVAILABLE,
    )
    engine = PoliticalSentimentEngine(SpeechMonitor(SourceRegistry((source,))))
    transcript = SpeechFixture(
        source_id="fixture", event_id="transcript-1", associated_event_id="event-1",
        revision=1, authority="Autoridade simulada", status=SpeechStatus.VERIFIED,
        speech_at=EVENT, published_at=at(1), received_at=at(received),
        verified_at=at(verified), provenance="fixture:documento",
        evidence=(EvidenceReference("documento", "evidence-1", 1, at(1)),),
        text=text or f"Melhora fiscal. Alta para {asset}.",
    )
    (interpretation,) = engine.interpret((transcript,), as_of=at(interpreted))
    return next(
        item for item in engine.hypothesize(
            interpretation, fixtures=(transcript,), as_of=at(created),
        ) if item.asset.value == asset
    )


def context(offset, price, volume, flow, *, contract="WINZ26", received=None):
    received = at(offset if received is None else received)
    mtf = MultiTimeframeState()
    mtf.update_tick(symbol=contract, price=price, cumulative_volume=volume, timestamp=received)
    return AnalysisContext(
        market=MarketState(symbol=contract, last_price=price, volume=0),
        multi_timeframe=mtf, order_flow_state=flow,
        source_timestamp=at(offset).isoformat(), received_timestamp=received,
    )


def market(*, prices=(100, 100, 100, 101, 102, 103), offsets=(-60, -30, 0, 15, 30, 60),
           contract="WINZ26", reverse_flow=False):
    state = OrderFlowState()
    output = []
    for index, (offset, price) in enumerate(zip(offsets, prices, strict=True)):
        size = index * 5.0
        state.update(0 if reverse_flow else size, size if reverse_flow else 0)
        item = context(offset, price, 1000 + index * 10, state, contract=contract)
        output.append(REPLAY.capture_next(lambda: item))
    return tuple(output)


def evaluate(samples=(), *, claim=None, contract="WINZ26", session=SESSION, cutoff=60,
             windows=MarketWindows(), concurrent=()):
    claim = claim if claim is not None else hypothesis(asset=contract[:3])
    return VALIDATOR.evaluate(
        claim, samples, contract=contract, session=session, as_of=at(cutoff),
        windows=windows, concurrent_events=concurrent,
    )


def test_compatible_market_records_timing_and_metrics_without_an_order():
    result = evaluate(market())
    assert result.result is ImpactResult.COMPATIBLE
    assert result.quality is SampleQuality.SUFFICIENT
    assert result.asset.value == "WIN"
    assert result.continuous and result.order_flow_available
    assert (result.pre_samples, result.post_samples) == (2, 3)
    assert (result.initial_at, result.final_at) == (at(15), at(60))
    assert (result.price_initial, result.price_final, result.absolute_change) == (101, 103, 2)
    assert result.percent_change == pytest.approx(200 / 101)
    assert (result.observed_volume, result.order_flow_delta) == (20, 10)
    timing = result.timing
    assert timing.event_time == EVENT
    assert (timing.published_at, timing.received_at, timing.verified_at) == (at(1), at(2), at(3))
    assert (timing.interpreted_at, timing.hypothesis_at, timing.available_at) == (at(4), at(5), at(5))
    assert result.observational_only and not result.order_execution_allowed
    assert not hasattr(result, "signal")


def test_no_market_data_and_outside_session_are_inconclusive():
    assert evaluate().reasons == ("NO_MARKET_DATA",)
    closed = MarketSession(at(-7200), at(-3600))
    assert evaluate(market(), session=closed).reasons == ("OUTSIDE_SESSION",)
    opens_during_window = MarketSession(at(-30), at(3600))
    closes_during_window = MarketSession(at(-3600), at(30))
    for session in (opens_during_window, closes_during_window):
        assert evaluate(market(), session=session).reasons == ("WINDOW_CROSSES_SESSION_BOUNDARY",)


def test_late_transcript_and_hypothesis_cannot_conclude_an_earlier_replay():
    claim = hypothesis(received=70, verified=71, interpreted=72, created=73)
    early = evaluate(market(), claim=claim)
    assert early.reasons == ("EVIDENCE_NOT_YET_AVAILABLE",)
    assert early.timing is None and early.price_initial is None
    late = evaluate(market(), claim=claim, cutoff=73)
    assert late.reasons == ("HYPOTHESIS_AFTER_EVENT_WINDOW",)
    assert late.timing.received_at == at(70)
    assert late.timing.available_at == at(73)
    assert late.observed_direction is None


def test_hypothesis_after_movement_excludes_the_pre_hypothesis_gain():
    samples = market(prices=(100, 100, 100, 105, 105, 105))
    claim = hypothesis(created=30)
    result = evaluate(samples, claim=claim)
    assert (result.initial_at, result.final_at) == (at(30), at(60))
    assert result.absolute_change == 0
    assert result.reasons == ("LATERAL_MOVEMENT",)
    assert result.result is ImpactResult.INCONCLUSIVE


def test_market_receive_time_excludes_late_transmitted_context():
    samples = market()
    delayed = replace(samples[-1], received_timestamp=at(61))
    result = evaluate((*samples[:-1], delayed))
    assert result.final_at == at(30)
    assert result.price_final == 102
    assert evaluate(samples, cutoff=59).reasons == ("POST_WINDOW_NOT_ELAPSED",)


def test_unclosed_candles_are_not_used_as_complete_price_samples():
    samples = market()
    assert {candle.timeframe for candle in samples[0].candles} == {"M1", "M5", "M15"}
    assert not any(candle.closed for sample in samples for candle in sample.candles)
    result = evaluate((samples[0], samples[-1]))
    assert result.reasons == ("INSUFFICIENT_WINDOW_SAMPLES",)
    assert result.quality is SampleQuality.INSUFFICIENT
    assert result.price_final is None


@pytest.mark.parametrize("flag", [Continuity.GAP, Continuity.REBASE])
def test_explicit_gap_or_rebase_prevents_direction(flag):
    samples = list(market())
    samples[2] = replace(samples[2], continuity=flag)
    result = evaluate(samples)
    assert result.reasons == ("MARKET_CONTINUITY_GAP",)
    assert not result.continuous
    assert result.observed_volume is None


def test_timestamp_gap_is_detected_even_without_explicit_flags():
    samples = market()
    assert evaluate((*samples[:1], *samples[2:])).reasons == ("MARKET_CONTINUITY_GAP",)


def test_missing_or_rebased_volume_remains_unknown():
    samples = market()
    for final_volume in (None, 900):
        result = evaluate((*samples[:-1], replace(samples[-1], cumulative_volume=final_volume)))
        assert result.reasons == ("VOLUME_UNAVAILABLE_OR_REBASED",)
        assert result.observed_volume is None and result.order_flow_available
        assert result.result is ImpactResult.INCONCLUSIVE
    flat = tuple(replace(sample, cumulative_volume=1000) for sample in samples)
    assert evaluate(flat).observed_volume == 0


def test_absent_order_flow_is_inconclusive_but_keeps_price_and_volume():
    samples = market()
    result = evaluate((*samples[:-1], replace(samples[-1], order_flow=None)))
    assert result.reasons == ("ORDER_FLOW_UNAVAILABLE_OR_REBASED",)
    assert not result.order_flow_available
    assert result.observed_volume == 20 and result.price_final == 103


def test_contradictory_order_flow_does_not_confirm_a_price_direction():
    result = evaluate(market(reverse_flow=True))
    assert result.observed_direction is ImpactDirection.UP
    assert result.order_flow_delta == -10
    assert result.result is ImpactResult.INCONCLUSIVE
    assert result.reasons == ("ORDER_FLOW_CONTRADICTS_PRICE",)


@pytest.mark.parametrize("original,new", [("WINZ26", "WING27"), ("WDOZ26", "WDOF27")])
def test_rollover_never_combines_contracts(original, new):
    before = market(contract=original)
    after = market(contract=new)
    assert evaluate((*before[:3], *after[3:]), contract=original).reasons == (
        "ROLLOVER_OR_MULTIPLE_CONTRACTS",
    )
    assert evaluate(after, contract=original).reasons == ("CONTRACT_NOT_OBSERVED",)


def test_other_root_is_ignored_and_mismatched_hypothesis_is_rejected():
    win = market()
    wdo = market(contract="WDOZ26")
    assert evaluate((*wdo, *win)) == evaluate(win)
    assert evaluate(wdo, contract="WDOZ26").result is ImpactResult.COMPATIBLE
    with pytest.raises(ValueError, match="root"):
        evaluate(wdo, contract="WDOZ26", claim=hypothesis())


def test_capture_uses_return_boundary_in_a_protected_offline_collector(monkeypatch, protected_chain):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    workbook.publish(quote(clock))
    baseline = REPLAY.capture_next(collector.get_data)
    initial_m1 = next(candle for candle in baseline.candles if candle.timeframe == "M1")
    assert baseline.cumulative_volume == 1000  # The Renko brick begins with zero volume.
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    exception = RuntimeError("interruption before get_data returned")

    def fail_after_acceptance(reason):
        raise exception

    with monkeypatch.context() as fault:
        fault.setattr(type(collector), "_report_protected_acceptance", staticmethod(fail_after_acceptance))
        with pytest.raises(RuntimeError) as raised:
            REPLAY.capture_next(collector.get_data)
        assert raised.value is exception
    workbook.publish(pending)
    assert REPLAY.capture_next(collector.get_data) is None

    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, price=180_080, volume=1200))
    delivered = REPLAY.capture_next(collector.get_data)
    assert delivered.cumulative_volume == 1200 and delivered.price == 180_080
    assert delivered.continuity is Continuity.GAP
    assert baseline.price == 180_000 and initial_m1.close == 180_000
    with pytest.raises(FrozenInstanceError):
        initial_m1.close = 180_060
    with pytest.raises(TypeError, match="delivered market projections"):
        evaluate((AnalysisContext(),))


def test_market_adapter_preserves_missing_volume_and_flow():
    raw = context(0, 100, 1000, None)
    sample = REPLAY.capture_next(lambda: raw, volume_available=False)
    assert sample.cumulative_volume is None
    assert sample.order_flow is None
    assert sample.source_timestamp == sample.received_timestamp == EVENT


def test_simultaneous_events_use_only_visible_evidence():
    other = EventRecord(
        source_id="calendar", event_id="event-2", revision=1,
        category=EventCategory.CONFIRMED_FACT, fact_status=FactStatus.OCCURRED,
        provenance="fixture:agenda", content="Outro evento", event_time=EVENT,
        published_at=EVENT, received_at=at(3), verified_at=at(4),
        evidence=(EvidenceReference("document", "notice", 1, EVENT),),
    )
    samples = market()
    assert evaluate(samples, concurrent=(other,)).reasons == ("SIMULTANEOUS_EVENTS",)
    late = replace(other, received_at=at(61), verified_at=at(62))
    assert evaluate(samples, concurrent=(late,)).result is ImpactResult.COMPATIBLE


def test_divergent_and_lateral_move_are_distinguished():
    downward = market(prices=(108, 107, 106, 105, 104, 102), reverse_flow=True)
    result = evaluate(downward)
    assert result.result is ImpactResult.DIVERGENT
    assert result.observed_direction is ImpactDirection.DOWN
    lateral = market(prices=(100, 100, 100, 100, 100, 100.01))
    assert evaluate(lateral).reasons == ("LATERAL_MOVEMENT",)
    neutral = hypothesis(text="Cerimonia institucional.")
    assert evaluate(lateral, claim=neutral).result is ImpactResult.COMPATIBLE


def test_uncertain_hypothesis_is_never_confirmed_from_observed_direction():
    claim = hypothesis(text="Talvez haja melhora fiscal e alta para WIN.")
    result = evaluate(market(), claim=claim)
    assert claim.direction is ImpactDirection.UNCERTAIN
    assert result.observed_direction is ImpactDirection.UP
    assert result.reasons == ("HYPOTHESIS_UNCERTAIN",)
    assert result.result is ImpactResult.INCONCLUSIVE


@pytest.mark.parametrize("minutes", [5, 15])
def test_configurable_windows_use_sample_coverage_not_candle_duration(minutes):
    boundary = timedelta(minutes=minutes)
    seconds = int(boundary.total_seconds())
    samples = market(offsets=(-seconds, -seconds // 2, 0, seconds // 4, seconds // 2, seconds))
    windows = MarketWindows(before=boundary, after=boundary, max_gap=boundary / 2)
    assert evaluate(samples, windows=windows, cutoff=seconds).result is ImpactResult.COMPATIBLE

