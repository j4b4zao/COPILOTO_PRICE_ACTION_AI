from analysis.replay.order_flow_ab_session_report import OrderFlowABSessionReporter
from analysis.replay.score_order_flow_ab_recorder import ScoreOrderFlowABRecorder
from core.analysis_context import AnalysisContext


def _record(recorder, *, status="ALIGNED", momentum="ACCELERATING_BUY", bias="BUY", total=75.0, persistence=1.0, impulse=1.0, strategy_valid=True):
    context = AnalysisContext()
    context.strategy.valid = strategy_valid
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = strategy_valid and total >= 70.0
    context.score.bias = bias
    context.checklist.order_flow_status = status
    context.checklist.order_flow_momentum = momentum
    context.checklist.order_flow_delta_persistence = persistence
    context.checklist.order_flow_delta_impulse_ratio = impulse
    return recorder.record(context)


def test_empty_session_returns_no_data():
    report = OrderFlowABSessionReporter().build(ScoreOrderFlowABRecorder())
    assert report.samples == 0
    assert report.dominant_effect == "NO_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_positive_session_is_detected():
    recorder = ScoreOrderFlowABRecorder()
    for _ in range(100):
        _record(recorder, status="ALIGNED")
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.dominant_effect == "POSITIVE"
    assert report.average_delta > 0
    assert report.recommendation == "KEEP_OBSERVING"


def test_negative_session_is_detected():
    recorder = ScoreOrderFlowABRecorder()
    for _ in range(100):
        _record(recorder, status="CONFLICT")
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.dominant_effect == "NEGATIVE"
    assert report.average_delta < 0


def test_neutral_session_is_detected():
    recorder = ScoreOrderFlowABRecorder()
    for _ in range(100):
        _record(recorder, status="MIXED", momentum="MIXED")
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.dominant_effect == "NEUTRAL"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_mixed_session_is_detected():
    recorder = ScoreOrderFlowABRecorder()
    for _ in range(50):
        _record(recorder, status="ALIGNED")
    for _ in range(50):
        _record(recorder, status="CONFLICT")
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.dominant_effect == "MIXED"
    assert report.recommendation == "KEEP_OBSERVING"


def test_less_than_minimum_samples_collects_more_data():
    recorder = ScoreOrderFlowABRecorder()
    for _ in range(99):
        _record(recorder, status="ALIGNED")
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_grade_or_validity_change_requires_review():
    recorder = ScoreOrderFlowABRecorder()
    for _ in range(99):
        _record(recorder, status="ALIGNED", total=75.0)
    _record(recorder, status="ALIGNED", total=69.0)
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.grade_changes >= 1 or report.validity_changes >= 1
    assert report.recommendation == "REVIEW_BEFORE_ENABLE"


def test_best_and_worst_scenarios_are_identified():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, status="ALIGNED", momentum="ACCELERATING_BUY", persistence=1.0, impulse=1.0)
    _record(recorder, status="CONFLICT", momentum="ACCELERATING_SELL", persistence=1.0, impulse=1.0)
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.best_average_delta > report.worst_average_delta
    assert report.best_scenario != "NONE"
    assert report.worst_scenario != "NONE"


def test_average_strength_is_reported():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, persistence=1.0, impulse=0.0)
    report = OrderFlowABSessionReporter().build(recorder)
    assert report.average_strength == 0.6


def test_report_build_is_readonly_and_rejects_invalid_contract():
    reporter = OrderFlowABSessionReporter()
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder)
    before = recorder.samples
    reporter.build(recorder)
    assert recorder.samples == before

    try:
        reporter.build(object())
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError esperado")
