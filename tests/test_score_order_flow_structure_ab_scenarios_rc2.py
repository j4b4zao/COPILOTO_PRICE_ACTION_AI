from core.analysis_context import AnalysisContext
from analysis.replay.score_order_flow_structure_ab_recorder import ScoreOrderFlowStructureABRecorder


def _record(recorder, *, total=75.0, bias="BUY", direction="BUY", alignment="ALIGNED", confidence=0.8):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = bias
    checklist = context.checklist
    checklist.order_flow_pattern_direction = direction
    checklist.order_flow_structure_alignment = alignment
    checklist.order_flow_structural_confidence = confidence
    return recorder.record(context)


def test_groups_by_alignment():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, alignment="ALIGNED")
    _record(recorder, alignment="CONFLICT")
    summary = recorder.scenario_summary()
    assert summary["by_alignment"]["ALIGNED"]["samples"] == 1
    assert summary["by_alignment"]["CONFLICT"]["samples"] == 1


def test_groups_by_pattern_direction():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, direction="BUY")
    _record(recorder, bias="SELL", direction="SELL")
    summary = recorder.scenario_summary()
    assert summary["by_pattern_direction"]["BUY"]["samples"] == 1
    assert summary["by_pattern_direction"]["SELL"]["samples"] == 1


def test_groups_by_bias():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, bias="BUY")
    _record(recorder, bias="SELL", direction="SELL")
    summary = recorder.scenario_summary()
    assert summary["by_bias"]["BUY"]["samples"] == 1
    assert summary["by_bias"]["SELL"]["samples"] == 1


def test_confidence_buckets():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, confidence=0.0)
    _record(recorder, confidence=0.3)
    _record(recorder, confidence=0.6)
    _record(recorder, confidence=0.9)
    summary = recorder.scenario_summary()["by_confidence"]
    assert summary["UNAVAILABLE"]["samples"] == 1
    assert summary["LOW"]["samples"] == 1
    assert summary["MEDIUM"]["samples"] == 1
    assert summary["HIGH"]["samples"] == 1


def test_aligned_same_bias_is_positive():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, bias="BUY", direction="BUY", alignment="ALIGNED", confidence=1.0)
    metrics = recorder.scenario(alignment="ALIGNED", bias="BUY", pattern_direction="BUY")
    assert metrics["positive_adjustments"] == 1
    assert metrics["average_delta"] == 1.5


def test_aligned_against_bias_is_negative():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, bias="BUY", direction="SELL", alignment="ALIGNED", confidence=1.0)
    metrics = recorder.scenario(alignment="ALIGNED", bias="BUY", pattern_direction="SELL")
    assert metrics["negative_adjustments"] == 1
    assert metrics["average_delta"] == -1.5


def test_conflict_same_bias_is_negative():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, bias="BUY", direction="BUY", alignment="CONFLICT", confidence=1.0)
    metrics = recorder.scenario(alignment="CONFLICT")
    assert metrics["average_delta"] == -1.12


def test_neutral_effect_is_small():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, bias="BUY", direction="BUY", alignment="NEUTRAL", confidence=1.0)
    metrics = recorder.scenario(alignment="NEUTRAL")
    assert metrics["average_delta"] == 0.38


def test_combined_filter_and_average_confidence():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder, bias="BUY", direction="BUY", alignment="ALIGNED", confidence=0.8)
    _record(recorder, bias="SELL", direction="SELL", alignment="ALIGNED", confidence=0.6)
    metrics = recorder.scenario(alignment="ALIGNED", bias="BUY", confidence="HIGH")
    assert metrics["samples"] == 1
    assert metrics["average_confidence"] == 0.8


def test_scenario_queries_do_not_mutate_samples():
    recorder = ScoreOrderFlowStructureABRecorder()
    _record(recorder)
    before = recorder.samples
    recorder.scenario_summary()
    recorder.scenario(alignment="ALIGNED")
    assert recorder.samples == before
