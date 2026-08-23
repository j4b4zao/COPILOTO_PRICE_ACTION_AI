from analysis.replay.order_flow_structure_ab_session_report import (
    OrderFlowStructureABSessionReporter,
)
from analysis.replay.score_order_flow_structure_ab_recorder import (
    ScoreOrderFlowStructureABRecorder,
    ScoreOrderFlowStructureABSample,
)


def _sample(delta=0.5, *, confidence=0.8, alignment="ALIGNED", direction="BUY", bias="BUY", grade=False, validity=False):
    return ScoreOrderFlowStructureABSample(
        baseline_total=80.0,
        adjusted_total=80.0 + delta,
        delta=delta,
        baseline_grade="A",
        adjusted_grade="A+" if grade else "A",
        grade_changed=grade,
        baseline_valid=True,
        adjusted_valid=not validity,
        validity_changed=validity,
        bias=bias,
        pattern_direction=direction,
        structure_alignment=alignment,
        structural_confidence=confidence,
        confidence_bucket="HIGH" if confidence >= 0.75 else "MEDIUM",
        adjustment=delta,
        passive_only=True,
    )


def test_empty_session():
    report = OrderFlowStructureABSessionReporter().build(ScoreOrderFlowStructureABRecorder())
    assert report.dominant_effect == "NO_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_positive_effect():
    recorder = ScoreOrderFlowStructureABRecorder()
    for _ in range(100):
        recorder.add_sample(_sample(delta=0.5))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.dominant_effect == "POSITIVE"
    assert report.recommendation == "KEEP_OBSERVING"


def test_negative_effect():
    recorder = ScoreOrderFlowStructureABRecorder()
    for _ in range(100):
        recorder.add_sample(_sample(delta=-0.5, direction="SELL", bias="BUY"))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.dominant_effect == "NEGATIVE"


def test_neutral_effect():
    recorder = ScoreOrderFlowStructureABRecorder()
    for _ in range(100):
        recorder.add_sample(_sample(delta=0.0, confidence=0.0, alignment="UNAVAILABLE", direction="NONE", bias="NONE"))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.dominant_effect == "NEUTRAL"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_mixed_effect():
    recorder = ScoreOrderFlowStructureABRecorder()
    for _ in range(50):
        recorder.add_sample(_sample(delta=0.5))
        recorder.add_sample(_sample(delta=-0.5, direction="SELL", bias="BUY"))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.dominant_effect == "MIXED"


def test_minimum_samples_rule():
    recorder = ScoreOrderFlowStructureABRecorder()
    for _ in range(99):
        recorder.add_sample(_sample())
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_grade_or_validity_change_forces_review():
    recorder = ScoreOrderFlowStructureABRecorder()
    for _ in range(99):
        recorder.add_sample(_sample())
    recorder.add_sample(_sample(grade=True, validity=True))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.grade_changes == 1
    assert report.validity_changes == 1
    assert report.recommendation == "REVIEW_BEFORE_ENABLE"


def test_best_and_worst_scenarios_are_exposed():
    recorder = ScoreOrderFlowStructureABRecorder()
    recorder.add_sample(_sample(delta=1.0, alignment="ALIGNED", confidence=0.9))
    recorder.add_sample(_sample(delta=-0.8, alignment="CONFLICT", direction="SELL", bias="BUY", confidence=0.8))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.best_scenario != "NONE"
    assert report.worst_scenario != "NONE"
    assert report.best_average_delta >= report.worst_average_delta


def test_average_confidence_is_reported():
    recorder = ScoreOrderFlowStructureABRecorder()
    recorder.add_sample(_sample(confidence=0.8))
    recorder.add_sample(_sample(confidence=0.6))
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert report.average_confidence == 0.7


def test_report_is_readonly_and_invalid_contract_rejected():
    recorder = ScoreOrderFlowStructureABRecorder()
    recorder.add_sample(_sample())
    before = recorder.samples
    report = OrderFlowStructureABSessionReporter().build(recorder)
    assert recorder.samples == before
    assert report.passive_only is True

    try:
        OrderFlowStructureABSessionReporter().build(object())
        raised = False
    except TypeError:
        raised = True
    assert raised is True
