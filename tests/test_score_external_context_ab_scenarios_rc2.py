from analysis.replay.score_external_context_ab_recorder import ScoreExternalContextABRecorder
from core.analysis_context import AnalysisContext


def _record(recorder, *, total=75.0, bias="BUY", status="ALIGNED", risk="RISK_ON", ext_bias="BULLISH", confidence=1.0):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = bias
    context.checklist.external_context_status = status
    context.checklist.external_context_confidence = confidence
    context.external_market.valid = status != "UNAVAILABLE"
    context.external_market.risk_on_off = risk
    context.external_market.global_bias = ext_bias
    context.external_market.confidence = confidence
    return recorder.record(context)


def test_groups_by_external_risk():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder, risk="RISK_ON")
    _record(recorder, bias="SELL", status="ALIGNED", risk="RISK_OFF", ext_bias="BEARISH")
    summary = recorder.scenario_summary()
    assert summary["by_risk"]["RISK_ON"]["samples"] == 1
    assert summary["by_risk"]["RISK_OFF"]["samples"] == 1


def test_groups_by_status():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder, status="ALIGNED")
    _record(recorder, status="CONFLICT")
    summary = recorder.scenario_summary()
    assert summary["by_status"]["ALIGNED"]["positive_adjustments"] == 1
    assert summary["by_status"]["CONFLICT"]["negative_adjustments"] == 1


def test_groups_by_bias():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder, bias="BUY")
    _record(recorder, bias="SELL", status="CONFLICT")
    summary = recorder.scenario_summary()
    assert summary["by_bias"]["BUY"]["samples"] == 1
    assert summary["by_bias"]["SELL"]["samples"] == 1


def test_confidence_buckets_are_exposed():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder, confidence=0.30, status="LOW_CONFIDENCE")
    _record(recorder, confidence=0.60)
    _record(recorder, confidence=0.90)
    summary = recorder.scenario_summary()
    assert summary["by_confidence"]["LOW"]["samples"] == 1
    assert summary["by_confidence"]["MEDIUM"]["samples"] == 1
    assert summary["by_confidence"]["HIGH"]["samples"] == 1


def test_unavailable_has_own_confidence_bucket():
    recorder = ScoreExternalContextABRecorder()
    sample = _record(recorder, status="UNAVAILABLE", risk="NEUTRAL", ext_bias="NEUTRAL", confidence=0.0)
    assert sample.confidence_bucket == "UNAVAILABLE"
    assert recorder.scenario(confidence="UNAVAILABLE")["samples"] == 1


def test_combined_filters_work():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder, bias="BUY", status="ALIGNED", risk="RISK_ON", confidence=0.90)
    _record(recorder, bias="SELL", status="ALIGNED", risk="RISK_OFF", ext_bias="BEARISH", confidence=0.90)
    metrics = recorder.scenario(risk="RISK_ON", status="ALIGNED", bias="BUY", confidence="HIGH")
    assert metrics["samples"] == 1
    assert metrics["positive_adjustments"] == 1


def test_risk_off_conflict_is_measured_separately():
    recorder = ScoreExternalContextABRecorder(weight=2.0)
    _record(recorder, status="CONFLICT", risk="RISK_OFF", ext_bias="BEARISH", confidence=0.80)
    metrics = recorder.scenario(risk="RISK_OFF", status="CONFLICT")
    assert metrics["samples"] == 1
    assert metrics["average_delta"] == -1.6


def test_average_confidence_is_reported():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder, confidence=0.60)
    _record(recorder, confidence=0.80)
    assert recorder.summary()["average_confidence"] == 0.7


def test_missing_scenario_returns_zero_metrics():
    recorder = ScoreExternalContextABRecorder()
    metrics = recorder.scenario(risk="RISK_OFF")
    assert metrics["samples"] == 0
    assert metrics["average_delta"] == 0.0
    assert metrics["average_confidence"] == 0.0


def test_scenario_queries_do_not_mutate_samples():
    recorder = ScoreExternalContextABRecorder()
    _record(recorder)
    before = recorder.samples
    recorder.scenario_summary()
    recorder.scenario(risk="RISK_ON", status="ALIGNED")
    assert recorder.samples == before
