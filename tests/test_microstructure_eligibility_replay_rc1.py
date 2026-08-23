from types import SimpleNamespace

from analysis.replay.microstructure_eligibility_replay_recorder import (
    MicrostructureEligibilityReplayRecorder,
)


def _context(pa="BUY", flow="BUY", book="BID_DOMINANT", correlated=False, book_available=True, book_conf=0.9):
    return SimpleNamespace(
        price_action=SimpleNamespace(bias=pa),
        order_flow=SimpleNamespace(
            pressure=flow,
            flow_momentum=f"PERSISTENT_{flow}" if flow in {"BUY", "SELL"} else "MIXED",
            pattern_direction=flow if flow in {"BUY", "SELL"} else "NONE",
            structure_alignment="ALIGNED",
            structural_pattern_confidence=0.9,
        ),
        book_depth_analysis=SimpleNamespace(
            valid=book_available,
            pressure=book if book_available else "UNAVAILABLE",
            concentration_bias=book if book_available else "BALANCED",
            confidence=book_conf if book_available else 0.0,
            duplicate_evidence_risk=correlated,
        ),
    )


def test_records_strong_candidate_with_three_independent_sources():
    recorder = MicrostructureEligibilityReplayRecorder()
    sample = recorder.record(_context())
    assert sample.state == "STRONG_CANDIDATE"
    assert sample.independent_evidence_count == 3


def test_correlated_book_downgrades_strong_to_promising():
    recorder = MicrostructureEligibilityReplayRecorder()
    sample = recorder.record(_context(correlated=True))
    assert sample.state == "PROMISING"
    assert sample.reason == "CORRELATED_EVIDENCE_DISCOUNT"


def test_conflict_becomes_not_eligible():
    recorder = MicrostructureEligibilityReplayRecorder()
    sample = recorder.record(_context(pa="BUY", flow="SELL", book="BID_DOMINANT"))
    assert sample.state == "NOT_ELIGIBLE"
    assert sample.conflict_count > 0


def test_missing_book_can_still_be_promising_with_two_sources():
    recorder = MicrostructureEligibilityReplayRecorder()
    sample = recorder.record(_context(book_available=False))
    assert sample.independent_evidence_count == 2
    assert sample.state in {"PROMISING", "OBSERVABLE"}


def test_summary_counts_all_states():
    recorder = MicrostructureEligibilityReplayRecorder()
    recorder.record(_context())
    recorder.record(_context(correlated=True))
    recorder.record(_context(pa="BUY", flow="SELL", book="ASK_DOMINANT"))
    summary = recorder.summary()
    assert summary["strong_candidate_samples"] == 1
    assert summary["promising_samples"] == 1
    assert summary["not_eligible_samples"] == 1


def test_rates_are_normalized():
    recorder = MicrostructureEligibilityReplayRecorder()
    recorder.record(_context())
    recorder.record(_context(correlated=True))
    rates = recorder.rates()
    assert rates["strong_candidate_rate"] == 0.5
    assert rates["promising_rate"] == 0.5


def test_empty_rates_are_zero():
    rates = MicrostructureEligibilityReplayRecorder().rates()
    assert all(value == 0.0 for value in rates.values())


def test_max_samples_retention():
    recorder = MicrostructureEligibilityReplayRecorder(max_samples=2)
    recorder.record(_context())
    recorder.record(_context(correlated=True))
    recorder.record(_context(pa="BUY", flow="SELL", book="ASK_DOMINANT"))
    assert recorder.size == 2


def test_samples_property_is_immutable_tuple():
    recorder = MicrostructureEligibilityReplayRecorder()
    recorder.record(_context())
    assert isinstance(recorder.samples, tuple)


def test_record_does_not_mutate_context():
    context = _context()
    before = (
        context.price_action.bias,
        context.order_flow.pressure,
        context.book_depth_analysis.pressure,
    )
    MicrostructureEligibilityReplayRecorder().record(context)
    after = (
        context.price_action.bias,
        context.order_flow.pressure,
        context.book_depth_analysis.pressure,
    )
    assert after == before
