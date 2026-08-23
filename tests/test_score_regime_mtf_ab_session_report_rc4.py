from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder
from analysis.replay.score_regime_mtf_ab_session_report import ScoreRegimeMtfABSessionReporter
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
    recorder.record(context)


def test_empty_session_report_requests_data():
    report = ScoreRegimeMtfABSessionReporter.build(ScoreRegimeMtfABRecorder())
    assert report.samples == 0
    assert report.recommendation == "NO_DATA"
    assert report.passive_only is True


def test_small_session_recommends_collect_more_data():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_positive_effect_is_detected():
    recorder = ScoreRegimeMtfABRecorder()
    for _ in range(3):
        _record(recorder)
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.dominant_effect == "POSITIVE"
    assert report.average_delta == 3.0


def test_negative_effect_is_detected():
    recorder = ScoreRegimeMtfABRecorder()
    for _ in range(3):
        _record(recorder, alignment="CONFLICT_REGIME", regime="TREND_DOWN", compatible=False)
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.dominant_effect == "NEGATIVE"
    assert report.average_delta == -3.0


def test_neutral_effect_is_detected():
    recorder = ScoreRegimeMtfABRecorder()
    for _ in range(3):
        _record(recorder, alignment="WAIT_TRIGGER")
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.dominant_effect == "NEUTRAL"


def test_mixed_effect_is_detected_on_tie():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    _record(recorder, alignment="CONFLICT_REGIME", regime="TREND_DOWN", compatible=False)
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.dominant_effect == "MIXED"


def test_strongest_scenarios_are_reported():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder, bias="BUY", alignment="BUY", regime="TREND_UP")
    _record(recorder, bias="BUY", alignment="WAIT_REGIME", regime="RANGE", compatible=False)
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.strongest_positive_scenario != "NONE"
    assert report.strongest_negative_scenario != "NONE"


def test_report_is_frozen_and_serializable():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    payload = report.to_dict()
    assert payload["version"].startswith("RC4-")
    assert payload["passive_only"] is True


def test_large_session_with_validity_changes_requires_review():
    recorder = ScoreRegimeMtfABRecorder()
    for _ in range(100):
        _record(recorder, total=69.0, alignment="BUY", regime="TREND_UP")
    report = ScoreRegimeMtfABSessionReporter.build(recorder)
    assert report.validity_changes > 0
    assert report.recommendation == "REVIEW_BEFORE_ENABLE"


def test_report_generation_does_not_mutate_recorder():
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    before = recorder.samples
    ScoreRegimeMtfABSessionReporter.build(recorder)
    assert recorder.samples == before
