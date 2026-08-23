from types import SimpleNamespace

from analysis.replay.score_book_depth_ab_recorder import ScoreBookDepthABRecorder


def _context(*, total=75.0, grade="B", valid=True, bias="BUY", status="ALIGNED", pressure="BID_DOMINANT", confidence=0.8, duplicate=False, strategy_valid=True):
    return SimpleNamespace(
        score=SimpleNamespace(total=total, grade=grade, valid=valid, bias=bias),
        strategy=SimpleNamespace(valid=strategy_valid),
        checklist=SimpleNamespace(
            book_depth_status=status,
            book_depth_pressure=pressure,
            book_depth_confidence=confidence,
            book_depth_duplicate_evidence_risk=duplicate,
        ),
    )


def test_groups_by_status():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context(status="ALIGNED"))
    recorder.record(_context(status="CONFLICT", pressure="ASK_DOMINANT"))
    grouped = recorder.scenario_summary()["by_status"]
    assert grouped["ALIGNED"]["samples"] == 1
    assert grouped["CONFLICT"]["samples"] == 1


def test_groups_by_pressure():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context(pressure="BID_DOMINANT"))
    recorder.record(_context(status="CONFLICT", pressure="ASK_DOMINANT"))
    grouped = recorder.scenario_summary()["by_pressure"]
    assert grouped["BID_DOMINANT"]["positive_adjustments"] == 1
    assert grouped["ASK_DOMINANT"]["negative_adjustments"] == 1


def test_groups_by_bias():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context(bias="BUY"))
    recorder.record(_context(bias="SELL", pressure="ASK_DOMINANT"))
    grouped = recorder.scenario_summary()["by_bias"]
    assert grouped["BUY"]["samples"] == 1
    assert grouped["SELL"]["samples"] == 1


def test_correlation_bucket_tracks_discounted_samples():
    recorder = ScoreBookDepthABRecorder()
    independent = recorder.record(_context(confidence=1.0, duplicate=False))
    correlated = recorder.record(_context(confidence=1.0, duplicate=True))
    grouped = recorder.scenario_summary()["by_correlation"]
    assert independent.correlation_bucket == "INDEPENDENT"
    assert correlated.correlation_bucket == "CORRELATED"
    assert correlated.effective_strength == 0.35
    assert grouped["CORRELATED"]["duplicate_samples"] == 1


def test_confidence_buckets():
    recorder = ScoreBookDepthABRecorder()
    low = recorder.record(_context(confidence=0.2))
    medium = recorder.record(_context(confidence=0.5))
    high = recorder.record(_context(confidence=0.8))
    unavailable = recorder.record(_context(status="UNAVAILABLE", pressure="UNAVAILABLE", confidence=0.9))
    assert low.confidence_bucket == "LOW"
    assert medium.confidence_bucket == "MEDIUM"
    assert high.confidence_bucket == "HIGH"
    assert unavailable.confidence_bucket == "UNAVAILABLE"


def test_combined_filters_select_exact_scenario():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context(bias="BUY", status="ALIGNED", pressure="BID_DOMINANT", confidence=0.85, duplicate=False))
    recorder.record(_context(bias="BUY", status="ALIGNED", pressure="BID_DOMINANT", confidence=0.85, duplicate=True))
    recorder.record(_context(bias="SELL", status="CONFLICT", pressure="BID_DOMINANT", confidence=0.85, duplicate=False))
    result = recorder.scenario(
        status="aligned",
        pressure="bid_dominant",
        bias="buy",
        correlation="independent",
        confidence="high",
    )
    assert result["samples"] == 1
    assert result["positive_adjustments"] == 1


def test_metrics_include_average_confidence_and_strength():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context(confidence=0.8, duplicate=False))
    recorder.record(_context(confidence=0.4, duplicate=True))
    summary = recorder.summary()
    assert summary["average_confidence"] == 0.6
    assert summary["average_effective_strength"] == 0.47


def test_neutral_status_remains_neutral_in_scenarios():
    recorder = ScoreBookDepthABRecorder()
    sample = recorder.record(_context(status="NEUTRAL", pressure="BALANCED", confidence=0.9))
    assert sample.delta == 0.0
    result = recorder.scenario(status="NEUTRAL")
    assert result["neutral_adjustments"] == 1


def test_empty_combined_filter_returns_zero_metrics():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context())
    result = recorder.scenario(status="CONFLICT", correlation="CORRELATED")
    assert result["samples"] == 0
    assert result["average_delta"] == 0.0
    assert result["average_confidence"] == 0.0


def test_scenario_queries_do_not_mutate_samples():
    recorder = ScoreBookDepthABRecorder()
    recorder.record(_context())
    before = recorder.samples
    recorder.scenario_summary()
    recorder.scenario(status="ALIGNED", confidence="HIGH")
    assert recorder.samples == before
