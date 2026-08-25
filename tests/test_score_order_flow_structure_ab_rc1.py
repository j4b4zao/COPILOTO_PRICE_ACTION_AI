from core.analysis_context import AnalysisContext
from analysis.replay.score_order_flow_structure_ab_recorder import ScoreOrderFlowStructureABRecorder


def _context(total=75.0, bias="BUY", direction="BUY", alignment="ALIGNED", confidence=1.0):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = ScoreOrderFlowStructureABRecorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = bias
    context.checklist.order_flow_pattern_direction = direction
    context.checklist.order_flow_structure_alignment = alignment
    context.checklist.order_flow_structural_confidence = confidence
    return context


def test_aligned_same_bias_adds_full_weight():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(_context())
    assert sample.delta == 1.5


def test_aligned_opposite_bias_penalizes():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(_context(direction="SELL"))
    assert sample.delta == -1.5


def test_conflict_same_bias_penalizes_with_factor():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(_context(alignment="CONFLICT"))
    assert sample.delta == -1.12


def test_conflict_opposite_bias_can_support_current_bias():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(
        _context(direction="SELL", alignment="CONFLICT")
    )
    assert sample.delta == 1.12


def test_neutral_alignment_has_small_effect():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(
        _context(alignment="NEUTRAL", confidence=0.8)
    )
    assert sample.delta == 0.3


def test_unavailable_and_none_direction_are_neutral():
    recorder = ScoreOrderFlowStructureABRecorder()
    assert recorder.record(_context(alignment="UNAVAILABLE")).delta == 0.0
    assert recorder.record(_context(direction="NONE")).delta == 0.0


def test_confidence_is_clamped():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(_context(confidence=2.0))
    assert sample.structural_confidence == 1.0
    assert sample.delta == 1.5


def test_total_is_clamped_to_score_bounds():
    up = ScoreOrderFlowStructureABRecorder().record(_context(total=99.5))
    down = ScoreOrderFlowStructureABRecorder().record(
        _context(total=0.5, direction="SELL", confidence=1.0)
    )
    assert up.adjusted_total == 100.0
    assert down.adjusted_total == 0.0


def test_grade_and_validity_changes_are_recorded():
    sample = ScoreOrderFlowStructureABRecorder(weight=1.5).record(_context(total=69.0))
    assert sample.grade_changed is True
    assert sample.validity_changed is True


def test_summary_and_context_immutability():
    recorder = ScoreOrderFlowStructureABRecorder()
    context = _context()
    before = (context.score.total, context.score.grade, context.score.valid, context.score.bias)
    recorder.record(context)
    summary = recorder.summary()
    assert summary["samples"] == 1
    assert summary["positive_adjustments"] == 1
    assert before == (context.score.total, context.score.grade, context.score.valid, context.score.bias)
