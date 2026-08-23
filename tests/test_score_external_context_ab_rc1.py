from analysis.replay.score_external_context_ab_recorder import ScoreExternalContextABRecorder
from core.analysis_context import AnalysisContext


def _context(*, total=75.0, grade="B", valid=True, strategy_valid=True, bias="BUY", status="ALIGNED", confidence=1.0, risk="RISK_ON", external_bias="BULLISH"):
    context = AnalysisContext()
    context.score.total = total
    context.score.grade = grade
    context.score.valid = valid
    context.score.bias = bias
    context.strategy.valid = strategy_valid
    context.checklist.external_context_status = status
    context.checklist.external_context_confidence = confidence
    context.external_market.valid = status != "UNAVAILABLE"
    context.external_market.risk_on_off = risk
    context.external_market.global_bias = external_bias
    context.external_market.confidence = confidence
    return context


def test_aligned_adds_up_to_two_points():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    sample = recorder.record(_context(status="ALIGNED", confidence=1.0))
    assert sample.adjustment == 2.0
    assert sample.adjusted_total == 77.0


def test_aligned_is_scaled_by_confidence():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    sample = recorder.record(_context(status="ALIGNED", confidence=0.75))
    assert sample.adjustment == 1.5


def test_conflict_subtracts_up_to_two_points():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    sample = recorder.record(_context(status="CONFLICT", confidence=1.0, risk="RISK_OFF", external_bias="BEARISH"))
    assert sample.adjustment == -2.0
    assert sample.adjusted_total == 73.0


def test_neutral_does_not_change_score():
    recorder = ScoreExternalContextABRecorder()
    sample = recorder.record(_context(status="NEUTRAL", confidence=1.0, risk="NEUTRAL", external_bias="NEUTRAL"))
    assert sample.delta == 0.0


def test_low_confidence_does_not_change_score():
    recorder = ScoreExternalContextABRecorder()
    sample = recorder.record(_context(status="LOW_CONFIDENCE", confidence=0.49))
    assert sample.delta == 0.0


def test_unavailable_does_not_change_score():
    recorder = ScoreExternalContextABRecorder()
    sample = recorder.record(_context(status="UNAVAILABLE", confidence=0.0))
    assert sample.delta == 0.0
    assert sample.external_status == "UNAVAILABLE"


def test_adjusted_total_is_bounded():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    high = recorder.record(_context(total=99.5, grade="A+", status="ALIGNED", confidence=1.0))
    low = recorder.record(_context(total=0.5, grade="REPROVADO", valid=False, status="CONFLICT", confidence=1.0))
    assert high.adjusted_total == 100.0
    assert low.adjusted_total == 0.0


def test_grade_and_validity_changes_are_measured():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    sample = recorder.record(_context(total=69.0, grade="C", valid=False, status="ALIGNED", confidence=1.0))
    assert sample.adjusted_grade == "B"
    assert sample.grade_changed is True
    assert sample.adjusted_valid is True
    assert sample.validity_changed is True


def test_summary_counts_positive_negative_and_neutral():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    recorder.record(_context(status="ALIGNED", confidence=1.0))
    recorder.record(_context(status="CONFLICT", confidence=1.0))
    recorder.record(_context(status="NEUTRAL", confidence=1.0))
    summary = recorder.summary()
    assert summary["samples"] == 3
    assert summary["positive_adjustments"] == 1
    assert summary["negative_adjustments"] == 1
    assert summary["neutral_adjustments"] == 1


def test_recording_does_not_mutate_official_context():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    context = _context(status="ALIGNED", confidence=1.0)
    before = (context.score.total, context.score.grade, context.score.valid, context.decision.direction)
    recorder.record(context)
    after = (context.score.total, context.score.grade, context.score.valid, context.decision.direction)
    assert after == before
