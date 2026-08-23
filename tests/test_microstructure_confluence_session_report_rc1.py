from analysis.replay.microstructure_confluence_replay_recorder import (
    MicrostructureConfluenceReplayRecorder,
    MicrostructureConfluenceReplaySample,
)
from analysis.replay.microstructure_confluence_session_report import (
    MicrostructureConfluenceSessionReporter,
)


def _sample(quality="HIGH", independent=3, correlated=0, conflicts=0, confidence=0.8):
    return MicrostructureConfluenceReplaySample(
        state="CONFLICT" if conflicts else "CONFIRMED",
        direction="BUY",
        confluence_quality=quality,
        confidence=confidence,
        independent_evidence_count=independent,
        correlated_evidence_count=correlated,
        conflict_count=conflicts,
        price_action_bias="BUY",
        flow_direction="BUY",
        book_direction="BUY",
        book_available=True,
        book_correlated_with_delta=correlated > 0,
    )


def _recorder(samples):
    recorder = MicrostructureConfluenceReplayRecorder()
    for sample in samples:
        recorder.add_sample(sample)
    return recorder


def test_empty_session_is_no_data():
    report = MicrostructureConfluenceSessionReporter().build(MicrostructureConfluenceReplayRecorder())
    assert report.session_quality == "NO_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_less_than_100_samples_collects_more_data():
    report = MicrostructureConfluenceSessionReporter().build(_recorder([_sample() for _ in range(20)]))
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_strong_independent_confluence():
    samples = [_sample() for _ in range(40)] + [_sample("MEDIUM", 2) for _ in range(60)]
    report = MicrostructureConfluenceSessionReporter().build(_recorder(samples))
    assert report.session_quality == "STRONG_INDEPENDENT_CONFLUENCE"
    assert report.recommendation == "KEEP_OBSERVING"


def test_promising_session():
    samples = [_sample() for _ in range(15)] + [_sample("MEDIUM", 2) for _ in range(85)]
    report = MicrostructureConfluenceSessionReporter().build(_recorder(samples))
    assert report.session_quality == "PROMISING"


def test_weak_session():
    samples = [_sample("LOW", 1, confidence=0.3) for _ in range(100)]
    report = MicrostructureConfluenceSessionReporter().build(_recorder(samples))
    assert report.session_quality == "WEAK"


def test_conflict_degrades_session():
    samples = [_sample("LOW", 1, conflicts=1) for _ in range(30)] + [_sample("MEDIUM", 2) for _ in range(70)]
    report = MicrostructureConfluenceSessionReporter().build(_recorder(samples))
    assert report.session_quality == "DEGRADED_BY_CONFLICT"
    assert report.recommendation == "REVIEW_CONFLICTS"


def test_correlation_rate_is_reported():
    samples = [_sample(correlated=1) for _ in range(25)] + [_sample() for _ in range(75)]
    report = MicrostructureConfluenceSessionReporter().build(_recorder(samples))
    assert report.correlation_rate == 0.25


def test_three_source_rate_is_reported():
    samples = [_sample(independent=3) for _ in range(20)] + [_sample("MEDIUM", 2) for _ in range(80)]
    report = MicrostructureConfluenceSessionReporter().build(_recorder(samples))
    assert report.three_source_rate == 0.2


def test_average_confidence_is_reported():
    report = MicrostructureConfluenceSessionReporter().build(
        _recorder([_sample(confidence=0.8), _sample(confidence=0.6)])
    )
    assert report.average_confidence == 0.7


def test_report_is_readonly_and_does_not_mutate_recorder():
    recorder = _recorder([_sample(), _sample("MEDIUM", 2)])
    before = recorder.samples
    report = MicrostructureConfluenceSessionReporter().build(recorder)
    assert report.passive_only is True
    assert recorder.samples == before
