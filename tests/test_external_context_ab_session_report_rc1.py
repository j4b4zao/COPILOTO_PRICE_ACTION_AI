from analysis.replay.external_context_ab_session_report import (
    ExternalContextABSessionReporter,
)
from analysis.replay.score_external_context_ab_recorder import (
    ScoreExternalContextABRecorder,
)
from core.analysis_context import AnalysisContext


def _record(recorder, *, total=75.0, bias="BUY", status="ALIGNED", risk="RISK_ON", ext_bias="BULLISH", confidence=1.0):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = bias
    context.checklist.external_context_status = status
    context.checklist.external_context_confidence = confidence
    context.external_market.valid = status != "UNAVAILABLE"
    context.external_market.risk_on_off = risk
    context.external_market.global_bias = ext_bias
    context.external_market.confidence = confidence
    return recorder.record(context)


def test_empty_session_returns_no_data():
    report = ExternalContextABSessionReporter().build(ScoreExternalContextABRecorder())
    assert report.samples == 0
    assert report.dominant_effect == "NO_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_positive_session_is_detected():
    recorder = ScoreExternalContextABRecorder()
    for _ in range(100):
        _record(recorder, status="ALIGNED", confidence=1.0)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.dominant_effect == "POSITIVE"
    assert report.average_delta == 2.0


def test_negative_session_is_detected():
    recorder = ScoreExternalContextABRecorder()
    for _ in range(100):
        _record(recorder, status="CONFLICT", risk="RISK_OFF", ext_bias="BEARISH", confidence=1.0)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.dominant_effect == "NEGATIVE"
    assert report.average_delta == -2.0


def test_neutral_session_is_detected():
    recorder = ScoreExternalContextABRecorder()
    for _ in range(100):
        _record(recorder, status="NEUTRAL", risk="NEUTRAL", ext_bias="NEUTRAL", confidence=0.8)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.dominant_effect == "NEUTRAL"


def test_mixed_session_is_detected():
    recorder = ScoreExternalContextABRecorder()
    for _ in range(50):
        _record(recorder, status="ALIGNED", confidence=1.0)
    for _ in range(50):
        _record(recorder, status="CONFLICT", confidence=1.0)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.dominant_effect == "MIXED"


def test_less_than_100_samples_collects_more_data():
    recorder = ScoreExternalContextABRecorder()
    for _ in range(99):
        _record(recorder)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_grade_or_validity_changes_force_review():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    for _ in range(100):
        _record(recorder, total=69.0, status="ALIGNED", confidence=1.0)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.validity_changes > 0
    assert report.recommendation == "REVIEW_BEFORE_ENABLE"


def test_best_and_worst_scenarios_are_reported():
    recorder = ScoreExternalContextABRecorder()
    for _ in range(60):
        _record(recorder, status="ALIGNED", confidence=1.0)
    for _ in range(40):
        _record(recorder, status="CONFLICT", risk="RISK_OFF", confidence=1.0)
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.best_average_delta >= 0.0
    assert report.worst_average_delta <= 0.0
    assert report.best_scenario != "NONE"
    assert report.worst_scenario != "NONE"


def test_report_is_passive_and_does_not_mutate_samples():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder)
    before = recorder.samples
    report = ExternalContextABSessionReporter().build(recorder)
    assert report.passive_only is True
    assert recorder.samples == before


def test_invalid_recorder_is_rejected():
    try:
        ExternalContextABSessionReporter().build(object())
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError esperado")
