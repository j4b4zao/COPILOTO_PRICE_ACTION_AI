from analysis.replay.score_microstructure_eligibility_ab_recorder import (
    ScoreMicrostructureEligibilityABRecorder,
)
from core.analysis_context import AnalysisContext


def _base_context(total=80.0, grade="A", valid=True):
    context = AnalysisContext()
    context.score.total = total
    context.score.grade = grade
    context.score.valid = valid
    context.strategy.valid = True
    context.price_action.bias = "BUY"
    return context


def _flow_buy(context):
    context.order_flow.pressure = "BUY"
    context.order_flow.flow_momentum = "ACCELERATING_BUY"
    context.order_flow.pattern_direction = "BUY"
    context.order_flow.structure_alignment = "ALIGNED"
    context.order_flow.structural_pattern_confidence = 0.9


def _book_buy(context, *, correlated=False, confidence=0.9):
    book = context.book_depth_analysis
    book.valid = True
    book.pressure = "BID_DOMINANT"
    book.concentration_bias = "BID_DOMINANT"
    book.confidence = confidence
    book.duplicate_evidence_risk = correlated


def test_weight_above_limit_is_rejected():
    try:
        ScoreMicrostructureEligibilityABRecorder(weight=1.6)
    except ValueError:
        return
    raise AssertionError("peso acima do limite deveria falhar")


def test_strong_candidate_gets_maximum_bonus():
    context = _base_context()
    _flow_buy(context)
    _book_buy(context)
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.eligibility_state == "STRONG_CANDIDATE"
    assert sample.adjustment == 1.5
    assert sample.adjusted_total == 81.5


def test_correlated_book_downgrades_and_discounts_bonus():
    context = _base_context()
    _flow_buy(context)
    _book_buy(context, correlated=True)
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.eligibility_state == "PROMISING"
    assert sample.correlation_factor == 0.5
    assert sample.adjustment == 0.38


def test_promising_independent_gets_half_weight():
    context = _base_context()
    _flow_buy(context)
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.eligibility_state == "PROMISING"
    assert sample.adjustment == 0.75


def test_observable_gets_zero_bonus():
    context = _base_context()
    context.book_depth_analysis.valid = True
    context.book_depth_analysis.pressure = "BID_DOMINANT"
    context.book_depth_analysis.concentration_bias = "BID_DOMINANT"
    context.book_depth_analysis.confidence = 0.30
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.eligibility_state == "OBSERVABLE"
    assert sample.adjustment == 0.0


def test_conflict_blocks_adjustment():
    context = _base_context()
    context.order_flow.pressure = "SELL"
    context.order_flow.flow_momentum = "ACCELERATING_SELL"
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.eligibility_state == "NOT_ELIGIBLE"
    assert sample.conflict_count > 0
    assert sample.adjustment == 0.0


def test_hypothetical_grade_change_is_detected():
    context = _base_context(total=79.5, grade="B", valid=True)
    _flow_buy(context)
    _book_buy(context)
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.adjusted_grade == "A"
    assert sample.grade_changed is True


def test_hypothetical_validity_change_is_detected():
    context = _base_context(total=69.5, grade="C", valid=False)
    _flow_buy(context)
    _book_buy(context)
    sample = ScoreMicrostructureEligibilityABRecorder().record(context)
    assert sample.adjusted_valid is True
    assert sample.validity_changed is True


def test_score_and_decision_remain_immutable():
    context = _base_context()
    context.decision.action = "BUY"
    _flow_buy(context)
    _book_buy(context)
    recorder = ScoreMicrostructureEligibilityABRecorder()
    recorder.record(context)
    assert context.score.total == 80.0
    assert context.score.grade == "A"
    assert context.score.valid is True
    assert context.decision.action == "BUY"


def test_summary_counts_strong_and_correlated_samples():
    recorder = ScoreMicrostructureEligibilityABRecorder()
    strong = _base_context()
    _flow_buy(strong)
    _book_buy(strong)
    recorder.record(strong)
    correlated = _base_context()
    _flow_buy(correlated)
    _book_buy(correlated, correlated=True)
    recorder.record(correlated)
    summary = recorder.summary()
    assert summary["samples"] == 2
    assert summary["strong_candidate_samples"] == 1
    assert summary["promising_samples"] == 1
    assert summary["correlated_samples"] == 1
    assert summary["passive_only"] is True
