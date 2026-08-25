from analysis.replay.score_order_flow_ab_recorder import ScoreOrderFlowABRecorder
from core.analysis_context import AnalysisContext


def _record(
    recorder,
    *,
    total=75.0,
    bias="BUY",
    status="ALIGNED",
    momentum="ACCELERATING_BUY",
    persistence=0.8,
    impulse=0.8,
):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = bias
    checklist = context.checklist
    checklist.order_flow_status = status
    checklist.order_flow_momentum = momentum
    checklist.order_flow_delta_persistence = persistence
    checklist.order_flow_delta_impulse_ratio = impulse
    return recorder.record(context)


def test_groups_by_status():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, status="ALIGNED")
    _record(recorder, status="CONFLICT", momentum="ACCELERATING_SELL")
    summary = recorder.scenario_summary()
    assert summary["by_status"]["ALIGNED"]["positive_adjustments"] == 1
    assert summary["by_status"]["CONFLICT"]["negative_adjustments"] == 1


def test_groups_by_momentum():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, momentum="ACCELERATING_BUY")
    _record(recorder, momentum="PERSISTENT_BUY", persistence=0.8, impulse=0.3)
    summary = recorder.scenario_summary()
    assert summary["by_momentum"]["ACCELERATING_BUY"]["samples"] == 1
    assert summary["by_momentum"]["PERSISTENT_BUY"]["samples"] == 1


def test_groups_by_bias():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, bias="BUY")
    _record(recorder, bias="SELL", momentum="ACCELERATING_SELL")
    summary = recorder.scenario_summary()
    assert summary["by_bias"]["BUY"]["samples"] == 1
    assert summary["by_bias"]["SELL"]["samples"] == 1


def test_strength_buckets_low_medium_high():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, persistence=0.2, impulse=0.2)
    _record(recorder, persistence=0.5, impulse=0.5)
    _record(recorder, persistence=0.9, impulse=0.9)
    summary = recorder.scenario_summary()["by_strength"]
    assert summary["LOW"]["samples"] == 1
    assert summary["MEDIUM"]["samples"] == 1
    assert summary["HIGH"]["samples"] == 1


def test_accelerating_aligned_high_strength_is_positive():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    _record(recorder, status="ALIGNED", momentum="ACCELERATING_BUY", persistence=1.0, impulse=1.0)
    metrics = recorder.scenario(status="ALIGNED", momentum="ACCELERATING_BUY", strength="HIGH")
    assert metrics["samples"] == 1
    assert metrics["average_delta"] == 2.0


def test_conflict_high_strength_is_negative():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    _record(recorder, status="CONFLICT", momentum="ACCELERATING_SELL", persistence=1.0, impulse=1.0)
    metrics = recorder.scenario(status="CONFLICT", strength="HIGH")
    assert metrics["average_delta"] == -2.0


def test_fading_is_negative_but_lighter():
    recorder = ScoreOrderFlowABRecorder(weight=2.0)
    _record(recorder, status="FADING", momentum="FADING_BUY", persistence=1.0, impulse=1.0)
    metrics = recorder.scenario(status="FADING")
    assert metrics["average_delta"] == -0.5


def test_mixed_remains_neutral():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, status="MIXED", momentum="MIXED", persistence=1.0, impulse=1.0)
    metrics = recorder.scenario(momentum="MIXED")
    assert metrics["neutral_adjustments"] == 1
    assert metrics["average_delta"] == 0.0


def test_combined_filters_are_supported():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder, bias="BUY", status="ALIGNED", momentum="PERSISTENT_BUY", persistence=0.8, impulse=0.5)
    _record(recorder, bias="SELL", status="CONFLICT", momentum="PERSISTENT_BUY", persistence=0.8, impulse=0.5)
    metrics = recorder.scenario(status="ALIGNED", momentum="PERSISTENT_BUY", bias="BUY", strength="HIGH")
    assert metrics["samples"] == 1
    assert metrics["positive_adjustments"] == 1


def test_scenario_queries_do_not_mutate_samples():
    recorder = ScoreOrderFlowABRecorder()
    _record(recorder)
    before = recorder.samples
    recorder.scenario_summary()
    recorder.scenario(status="ALIGNED", strength="HIGH")
    assert recorder.samples == before
