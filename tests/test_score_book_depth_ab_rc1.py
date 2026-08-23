from types import SimpleNamespace

import pytest

from analysis.replay.score_book_depth_ab_recorder import ScoreBookDepthABRecorder


def _context(
    *,
    total=75.0,
    grade="B",
    score_valid=True,
    strategy_valid=True,
    bias="BUY",
    status="ALIGNED",
    pressure="BID_DOMINANT",
    confidence=0.8,
    duplicate=False,
):
    return SimpleNamespace(
        score=SimpleNamespace(
            total=total,
            grade=grade,
            valid=score_valid,
            bias=bias,
        ),
        strategy=SimpleNamespace(valid=strategy_valid),
        checklist=SimpleNamespace(
            book_depth_status=status,
            book_depth_pressure=pressure,
            book_depth_confidence=confidence,
            book_depth_duplicate_evidence_risk=duplicate,
        ),
    )


def test_aligned_book_adds_small_bonus():
    sample = ScoreBookDepthABRecorder().record(_context())
    assert sample.adjustment == 0.8
    assert sample.adjusted_total == 75.8


def test_conflict_subtracts_small_penalty():
    sample = ScoreBookDepthABRecorder().record(
        _context(status="CONFLICT", pressure="ASK_DOMINANT")
    )
    assert sample.adjustment == -0.8
    assert sample.adjusted_total == 74.2


def test_duplicate_delta_evidence_reduces_effect_to_35_percent():
    sample = ScoreBookDepthABRecorder().record(_context(duplicate=True))
    assert sample.correlation_factor == 0.35
    assert sample.effective_strength == 0.28
    assert sample.adjustment == 0.28


def test_neutral_or_unavailable_has_zero_effect():
    recorder = ScoreBookDepthABRecorder()
    neutral = recorder.record(_context(status="NEUTRAL"))
    unavailable = recorder.record(_context(status="UNAVAILABLE", confidence=1.0))
    assert neutral.delta == 0.0
    assert unavailable.delta == 0.0


def test_confidence_is_clamped():
    high = ScoreBookDepthABRecorder().record(_context(confidence=5.0))
    low = ScoreBookDepthABRecorder().record(_context(confidence=-2.0))
    assert high.confidence == 1.0
    assert low.confidence == 0.0


def test_adjusted_total_is_clamped_between_zero_and_100():
    recorder = ScoreBookDepthABRecorder()
    top = recorder.record(_context(total=99.8, grade="A+", confidence=1.0))
    bottom = recorder.record(
        _context(total=0.2, grade="REPROVADO", status="CONFLICT", confidence=1.0)
    )
    assert top.adjusted_total == 100.0
    assert bottom.adjusted_total == 0.0


def test_grade_change_is_detected():
    sample = ScoreBookDepthABRecorder().record(
        _context(total=79.6, grade="B", confidence=0.8)
    )
    assert sample.adjusted_grade == "A"
    assert sample.grade_changed is True


def test_validity_change_is_detected_around_min_score():
    sample = ScoreBookDepthABRecorder().record(
        _context(total=59.5, grade="REPROVADO", score_valid=False, confidence=1.0)
    )
    assert sample.adjusted_total == 60.5
    assert sample.adjusted_valid is True
    assert sample.validity_changed is True


def test_weight_above_one_is_rejected():
    with pytest.raises(ValueError):
        ScoreBookDepthABRecorder(weight=1.01)


def test_record_does_not_mutate_official_context():
    context = _context()
    before = (
        context.score.total,
        context.score.grade,
        context.score.valid,
        context.score.bias,
        context.strategy.valid,
        context.checklist.book_depth_status,
        context.checklist.book_depth_confidence,
    )
    ScoreBookDepthABRecorder().record(context)
    after = (
        context.score.total,
        context.score.grade,
        context.score.valid,
        context.score.bias,
        context.strategy.valid,
        context.checklist.book_depth_status,
        context.checklist.book_depth_confidence,
    )
    assert after == before
