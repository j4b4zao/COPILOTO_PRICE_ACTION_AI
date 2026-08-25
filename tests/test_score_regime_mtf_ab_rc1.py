from types import SimpleNamespace

import pytest

from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder


def _context(
    *,
    total=80.0,
    grade="A",
    valid=True,
    bias="BUY",
    strategy_valid=True,
    alignment="BUY",
    mtf_bias="BUY",
    regime_context="TREND_UP",
    regime_compatible=True,
):
    return SimpleNamespace(
        score=SimpleNamespace(
            total=total,
            grade=grade,
            valid=valid,
            bias=bias,
        ),
        strategy=SimpleNamespace(valid=strategy_valid),
        multi_timeframe_analysis=SimpleNamespace(
            valid=True,
            alignment=alignment,
            bias=mtf_bias,
            regime_context=regime_context,
            regime_compatible=regime_compatible,
        ),
        risk=SimpleNamespace(marker="risk-unchanged"),
        decision=SimpleNamespace(marker="decision-unchanged"),
    )


def test_buy_confirmation_adds_three_points():
    sample = ScoreRegimeMtfABRecorder().record(_context())
    assert sample.adjustment == 3.0
    assert sample.baseline_total == 80.0
    assert sample.adjusted_total == 83.0


def test_sell_confirmation_adds_three_points():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(
            bias="SELL",
            alignment="SELL",
            mtf_bias="SELL",
            regime_context="TREND_DOWN",
        )
    )
    assert sample.adjustment == 3.0
    assert sample.adjusted_total == 83.0


def test_conflict_regime_subtracts_full_weight():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(alignment="CONFLICT_REGIME", regime_compatible=False)
    )
    assert sample.adjustment == -3.0
    assert sample.adjusted_total == 77.0


def test_conflict_m1_subtracts_intermediate_weight():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(alignment="CONFLICT_M1", regime_compatible=False)
    )
    assert sample.adjustment == -2.25
    assert sample.adjusted_total == 77.75


def test_wait_regime_subtracts_half_weight():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(alignment="WAIT_REGIME", regime_context="TRANSITION", regime_compatible=False)
    )
    assert sample.adjustment == -1.5
    assert sample.adjusted_total == 78.5


def test_wait_trigger_is_neutral():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(alignment="WAIT_TRIGGER", regime_compatible=False)
    )
    assert sample.adjustment == 0.0
    assert sample.adjusted_total == sample.baseline_total


def test_grade_change_is_detected():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(total=89.0, grade="A")
    )
    assert sample.adjusted_total == 92.0
    assert sample.adjusted_grade == "A+"
    assert sample.grade_changed is True


def test_validity_change_is_detected_around_threshold():
    sample = ScoreRegimeMtfABRecorder().record(
        _context(
            total=71.0,
            grade="B",
            valid=True,
            alignment="CONFLICT_REGIME",
            regime_compatible=False,
        )
    )
    assert sample.adjusted_total == 68.0
    assert sample.adjusted_valid is False
    assert sample.validity_changed is True


def test_recorder_is_passive_and_does_not_mutate_context():
    context = _context()
    before = (
        context.score.total,
        context.score.grade,
        context.score.valid,
        context.risk.marker,
        context.decision.marker,
    )
    ScoreRegimeMtfABRecorder().record(context)
    after = (
        context.score.total,
        context.score.grade,
        context.score.valid,
        context.risk.marker,
        context.decision.marker,
    )
    assert after == before


def test_summary_and_weight_validation():
    recorder = ScoreRegimeMtfABRecorder(weight=3.0, max_samples=2)
    recorder.record(_context())
    recorder.record(_context(alignment="CONFLICT_REGIME", regime_compatible=False))
    recorder.record(_context(alignment="WAIT_TRIGGER", regime_compatible=False))

    summary = recorder.summary()
    assert recorder.size == 2
    assert summary["samples"] == 2
    assert summary["negative_adjustments"] == 1
    assert summary["neutral_adjustments"] == 1
    assert summary["weight"] == 3.0

    with pytest.raises(ValueError):
        ScoreRegimeMtfABRecorder(weight=5.1)
