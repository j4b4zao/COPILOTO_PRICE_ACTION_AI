from types import SimpleNamespace

from analysis.replay.microstructure_confluence_replay_recorder import (
    MicrostructureConfluenceReplayRecorder,
)


def _context(pa="BUY", flow="BUY", book="BID_DOMINANT", correlated=False, book_available=True):
    return SimpleNamespace(
        price_action=SimpleNamespace(bias=pa),
        order_flow=SimpleNamespace(
            pressure=flow,
            flow_momentum=f"PERSISTENT_{flow}" if flow in {"BUY", "SELL"} else "MIXED",
            pattern_direction=flow if flow in {"BUY", "SELL"} else "NONE",
            structure_alignment="ALIGNED",
            structural_pattern_confidence=0.8,
        ),
        book_depth_analysis=SimpleNamespace(
            valid=book_available,
            pressure=book if book_available else "UNAVAILABLE",
            concentration_bias=book if book_available else "BALANCED",
            confidence=0.8 if book_available else 0.0,
            duplicate_evidence_risk=correlated,
        ),
    )


def test_three_independent_sources_are_recorded():
    recorder = MicrostructureConfluenceReplayRecorder()
    sample = recorder.record(_context())
    assert sample.independent_evidence_count == 3
    assert sample.confluence_quality == "HIGH"


def test_correlated_book_does_not_increase_independent_count():
    recorder = MicrostructureConfluenceReplayRecorder()
    sample = recorder.record(_context(correlated=True))
    assert sample.independent_evidence_count == 2
    assert sample.correlated_evidence_count >= 1


def test_missing_book_keeps_two_independent_sources():
    recorder = MicrostructureConfluenceReplayRecorder()
    sample = recorder.record(_context(book_available=False))
    assert sample.independent_evidence_count == 2
    assert sample.book_available is False


def test_flow_conflict_is_recorded():
    recorder = MicrostructureConfluenceReplayRecorder()
    sample = recorder.record(_context(pa="BUY", flow="SELL"))
    assert sample.state == "CONFLICT"
    assert sample.conflict_count >= 1


def test_book_conflict_is_recorded():
    recorder = MicrostructureConfluenceReplayRecorder()
    sample = recorder.record(_context(pa="BUY", flow="BUY", book="ASK_DOMINANT"))
    assert sample.state == "CONFLICT"
    assert sample.conflict_count >= 1


def test_summary_groups_independent_evidence_counts():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.record(_context())
    recorder.record(_context(correlated=True))
    recorder.record(_context(book_available=False))
    summary = recorder.summary()
    assert summary["by_independent_evidence"][3] == 1
    assert summary["by_independent_evidence"][2] == 2


def test_distribution_reports_one_two_three_sources():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.record(_context())
    recorder.record(_context(book_available=False))
    one = _context(book_available=False)
    one.order_flow.pressure = "INSUFFICIENT_DATA"
    one.order_flow.flow_momentum = "INSUFFICIENT_DATA"
    one.order_flow.pattern_direction = "NONE"
    recorder.record(one)
    distribution = recorder.distribution()
    assert distribution["three_sources"] == 1
    assert distribution["two_sources"] == 1
    assert distribution["one_source"] == 1


def test_max_samples_retention():
    recorder = MicrostructureConfluenceReplayRecorder(max_samples=2)
    recorder.record(_context(pa="BUY"))
    recorder.record(_context(pa="SELL", flow="SELL", book="ASK_DOMINANT"))
    recorder.record(_context(pa="BUY"))
    assert recorder.size == 2


def test_samples_property_is_immutable_tuple():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.record(_context())
    assert isinstance(recorder.samples, tuple)


def test_record_does_not_mutate_source_context():
    context = _context()
    before = context.price_action.bias, context.order_flow.pressure, context.book_depth_analysis.pressure
    MicrostructureConfluenceReplayRecorder().record(context)
    after = context.price_action.bias, context.order_flow.pressure, context.book_depth_analysis.pressure
    assert after == before
