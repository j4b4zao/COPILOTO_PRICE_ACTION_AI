from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder
from core.analysis_context import AnalysisContext


def _record(recorder, *, total=75.0, bias="BUY", alignment="BUY", regime="TREND_UP", compatible=True):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = bias
    mtf = context.multi_timeframe_analysis
    mtf.valid = True
    mtf.bias = bias
    mtf.alignment = alignment
    mtf.regime_context = regime
    mtf.regime_compatible = compatible
    return recorder.record(context)


def test_scenario_summary_groups_by_regime():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder, regime="TREND_UP")
    _record(recorder, bias="SELL", alignment="SELL", regime="TREND_DOWN")
    summary = recorder.scenario_summary()
    assert summary["by_regime"]["TREND_UP"]["samples"] == 1
    assert summary["by_regime"]["TREND_DOWN"]["samples"] == 1


def test_scenario_summary_groups_by_alignment():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder, alignment="BUY")
    _record(recorder, alignment="CONFLICT_REGIME", compatible=False)
    summary = recorder.scenario_summary()
    assert summary["by_alignment"]["BUY"]["positive_adjustments"] == 1
    assert summary["by_alignment"]["CONFLICT_REGIME"]["negative_adjustments"] == 1


def test_scenario_summary_groups_by_bias():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder, bias="BUY", alignment="BUY", regime="TREND_UP")
    _record(recorder, bias="SELL", alignment="SELL", regime="TREND_DOWN")
    summary = recorder.scenario_summary()
    assert summary["by_bias"]["BUY"]["samples"] == 1
    assert summary["by_bias"]["SELL"]["samples"] == 1


def test_range_wait_regime_is_measured_separately():
    recorder = ScoreRegimeMtfABRecorder(weight=3.0)
    _record(recorder, alignment="WAIT_REGIME", regime="RANGE", compatible=False)
    metrics = recorder.scenario(regime="RANGE")
    assert metrics["samples"] == 1
    assert metrics["negative_adjustments"] == 1
    assert metrics["average_delta"] == -1.5


def test_transition_wait_regime_is_measured_separately():
    recorder = ScoreRegimeMtfABRecorder(weight=3.0)
    _record(recorder, alignment="WAIT_REGIME", regime="TRANSITION", compatible=False)
    metrics = recorder.scenario(regime="TRANSITION", alignment="WAIT_REGIME")
    assert metrics["samples"] == 1
    assert metrics["average_delta"] == -1.5


def test_conflict_regime_scenario_has_full_penalty():
    recorder = ScoreRegimeMtfABRecorder(weight=3.0)
    _record(recorder, alignment="CONFLICT_REGIME", regime="TREND_DOWN", compatible=False)
    metrics = recorder.scenario(alignment="CONFLICT_REGIME")
    assert metrics["average_delta"] == -3.0


def test_wait_trigger_scenario_remains_neutral():
    recorder = ScoreRegimeMtfABRecorder(weight=3.0)
    _record(recorder, alignment="WAIT_TRIGGER", regime="TREND_UP", compatible=True)
    metrics = recorder.scenario(alignment="WAIT_TRIGGER")
    assert metrics["neutral_adjustments"] == 1
    assert metrics["average_delta"] == 0.0


def test_combined_filters_are_supported():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder, bias="BUY", alignment="BUY", regime="TREND_UP")
    _record(recorder, bias="SELL", alignment="SELL", regime="TREND_DOWN")
    metrics = recorder.scenario(regime="TREND_UP", alignment="BUY", bias="BUY")
    assert metrics["samples"] == 1
    assert metrics["positive_adjustments"] == 1


def test_missing_scenario_returns_zero_metrics():
    recorder = ScoreRegimeMtfABRecorder()
    metrics = recorder.scenario(regime="UNKNOWN")
    assert metrics["samples"] == 0
    assert metrics["average_delta"] == 0.0


def test_scenario_queries_do_not_mutate_samples():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    before = recorder.samples
    recorder.scenario_summary()
    recorder.scenario(regime="TREND_UP")
    assert recorder.samples == before
