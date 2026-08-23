from analysis.replay.book_depth_ab_session_report import BookDepthABSessionReporter
from analysis.replay.score_book_depth_ab_recorder import (
    ScoreBookDepthABRecorder,
    ScoreBookDepthABSample,
)


def _sample(delta=0.2, correlation="INDEPENDENT", confidence=0.8, grade=False, validity=False):
    return ScoreBookDepthABSample(
        delta=delta,
        confidence=confidence,
        effective_strength=confidence if correlation == "INDEPENDENT" else round(confidence * 0.35, 4),
        correlation_bucket=correlation,
        duplicate_evidence_risk=correlation == "CORRELATED",
        grade_changed=grade,
        validity_changed=validity,
        status="ALIGNED" if delta > 0 else "CONFLICT" if delta < 0 else "NEUTRAL",
        pressure="BID_DOMINANT" if delta >= 0 else "ASK_DOMINANT",
        bias="BUY",
        confidence_bucket="HIGH",
    )


def _recorder(samples):
    recorder = ScoreBookDepthABRecorder()
    for sample in samples:
        recorder.add_sample(sample)
    return recorder


def test_empty_session_returns_no_data():
    report = BookDepthABSessionReporter().build(_recorder([]))
    assert report.dominant_effect == "NO_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_positive_session():
    report = BookDepthABSessionReporter().build(_recorder([_sample(0.2) for _ in range(100)]))
    assert report.dominant_effect == "POSITIVE"
    assert report.recommendation == "KEEP_OBSERVING"


def test_negative_session():
    report = BookDepthABSessionReporter().build(_recorder([_sample(-0.2) for _ in range(100)]))
    assert report.dominant_effect == "NEGATIVE"


def test_neutral_session():
    report = BookDepthABSessionReporter().build(_recorder([_sample(0.0) for _ in range(100)]))
    assert report.dominant_effect == "NEUTRAL"


def test_mixed_session():
    samples = [_sample(0.2) for _ in range(50)] + [_sample(-0.2) for _ in range(50)]
    report = BookDepthABSessionReporter().build(_recorder(samples))
    assert report.dominant_effect == "MIXED"


def test_requires_100_samples():
    report = BookDepthABSessionReporter().build(_recorder([_sample(0.2) for _ in range(99)]))
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_grade_or_validity_change_forces_review():
    samples = [_sample(0.2) for _ in range(98)] + [_sample(0.2, grade=True), _sample(0.2, validity=True)]
    report = BookDepthABSessionReporter().build(_recorder(samples))
    assert report.grade_changes == 1
    assert report.validity_changes == 1
    assert report.recommendation == "REVIEW_BEFORE_ENABLE"


def test_separates_independent_and_correlated_value():
    samples = [_sample(0.3, "INDEPENDENT") for _ in range(60)] + [_sample(0.1, "CORRELATED") for _ in range(40)]
    report = BookDepthABSessionReporter().build(_recorder(samples))
    assert report.independent_samples == 60
    assert report.correlated_samples == 40
    assert report.independent_average_delta == 0.3
    assert report.correlated_average_delta == 0.1
    assert report.independent_effect == "POSITIVE"
    assert report.correlated_effect == "POSITIVE"


def test_best_and_worst_scenarios_are_reported():
    samples = [_sample(0.4, "INDEPENDENT") for _ in range(60)] + [_sample(-0.2, "CORRELATED") for _ in range(40)]
    report = BookDepthABSessionReporter().build(_recorder(samples))
    assert report.best_scenario != "NONE"
    assert report.worst_scenario != "NONE"


def test_report_does_not_mutate_recorder():
    recorder = _recorder([_sample(0.2) for _ in range(100)])
    before = recorder.samples
    BookDepthABSessionReporter().build(recorder)
    assert recorder.samples == before
