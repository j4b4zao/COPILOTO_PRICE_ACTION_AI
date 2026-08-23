from analysis.replay.score_order_flow_ab_recorder import ScoreOrderFlowABRecorder
from core.analysis_context import AnalysisContext


def _context(*, total=75.0, status="ALIGNED", momentum="PERSISTENT_BUY", persistence=1.0, impulse=0.5):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = ScoreOrderFlowABRecorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = "BUY"
    checklist = context.checklist
    checklist.order_flow_status = status
    checklist.order_flow_momentum = momentum
    checklist.order_flow_delta_persistence = persistence
    checklist.order_flow_delta_impulse_ratio = impulse
    return context


def test_aligned_order_flow_adds_small_bonus():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    sample = recorder.record(_context(persistence=1.0, impulse=1.0))
    assert sample.delta == 2.0


def test_conflict_order_flow_subtracts_small_penalty():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    sample = recorder.record(_context(status="CONFLICT", persistence=1.0, impulse=1.0))
    assert sample.delta == -2.0


def test_fading_has_only_light_penalty():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    sample = recorder.record(_context(status="FADING", persistence=1.0, impulse=1.0))
    assert sample.delta == -0.5


def test_mixed_order_flow_is_neutral():
    recorder = ScoreOrderFlowABRecorder()
    sample = recorder.record(_context(status="MIXED"))
    assert sample.delta == 0.0


def test_unavailable_order_flow_is_neutral():
    recorder = ScoreOrderFlowABRecorder()
    sample = recorder.record(_context(status="UNAVAILABLE"))
    assert sample.delta == 0.0


def test_evidence_strength_combines_persistence_and_impulse():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    sample = recorder.record(_context(persistence=0.5, impulse=0.25))
    assert sample.evidence_strength == 0.4
    assert sample.delta == 0.8


def test_adjusted_total_is_bounded():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    high = recorder.record(_context(total=99.5, persistence=1.0, impulse=1.0))
    low = recorder.record(_context(total=0.5, status="CONFLICT", persistence=1.0, impulse=1.0))
    assert high.adjusted_total == 100.0
    assert low.adjusted_total == 0.0


def test_grade_and_validity_changes_are_measured():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    context = _context(total=69.0, persistence=1.0, impulse=1.0)
    context.score.valid = False
    sample = recorder.record(context)
    assert sample.grade_changed is True
    assert sample.validity_changed is True


def test_summary_accumulates_positive_negative_and_neutral():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    recorder.record(_context(status="ALIGNED"))
    recorder.record(_context(status="CONFLICT"))
    recorder.record(_context(status="MIXED"))
    summary = recorder.summary()
    assert summary["samples"] == 3
    assert summary["positive_adjustments"] == 1
    assert summary["negative_adjustments"] == 1
    assert summary["neutral_adjustments"] == 1


def test_recording_does_not_mutate_official_context():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    context = _context(total=75.0, status="ALIGNED")
    before_total = context.score.total
    before_valid = context.score.valid
    before_decision = context.decision.direction
    recorder.record(context)
    assert context.score.total == before_total
    assert context.score.valid == before_valid
    assert context.decision.direction == before_decision
