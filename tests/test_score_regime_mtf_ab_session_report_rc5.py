import json

import pytest

from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder
from analysis.replay.score_regime_mtf_ab_session_report import (
    ScoreRegimeMtfABSessionReporter,
)
from core.analysis_context import AnalysisContext


def _record(recorder, *, total=75.0, alignment="BUY", regime="TREND_UP"):
    context = AnalysisContext()
    context.strategy.valid = True
    context.score.total = total
    context.score.grade = recorder._grade(total)
    context.score.valid = total >= 70.0
    context.score.bias = "BUY"
    mtf = context.multi_timeframe_analysis
    mtf.valid = True
    mtf.bias = "BUY"
    mtf.alignment = alignment
    mtf.regime_context = regime
    mtf.regime_compatible = alignment == "BUY"
    recorder.record(context)


def test_export_json_round_trip(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    path = tmp_path / "session.json"
    ScoreRegimeMtfABSessionReporter.export_json(recorder, path)
    loaded = ScoreRegimeMtfABSessionReporter.load_json(path)
    assert loaded.samples == 1
    assert loaded.passive_only is True


def test_export_json_requires_json_extension(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    with pytest.raises(ValueError):
        ScoreRegimeMtfABSessionReporter.export_json(recorder, tmp_path / "session.txt")


def test_export_json_creates_parent_directory(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    path = tmp_path / "nested" / "session.json"
    ScoreRegimeMtfABSessionReporter.export_json(recorder, path)
    assert path.exists()


def test_empty_session_can_be_exported(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    path = tmp_path / "empty.json"
    ScoreRegimeMtfABSessionReporter.export_json(recorder, path)
    loaded = ScoreRegimeMtfABSessionReporter.load_json(path)
    assert loaded.samples == 0
    assert loaded.recommendation == "NO_DATA"


def test_load_json_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ScoreRegimeMtfABSessionReporter.load_json(tmp_path / "missing.json")


def test_load_json_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError):
        ScoreRegimeMtfABSessionReporter.load_json(path)


def test_load_json_non_object_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        ScoreRegimeMtfABSessionReporter.load_json(path)


def test_load_json_missing_fields_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"version": "x"}), encoding="utf-8")
    with pytest.raises(ValueError):
        ScoreRegimeMtfABSessionReporter.load_json(path)


def test_exported_report_keeps_dominant_effect(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    for _ in range(3):
        _record(recorder)
    path = tmp_path / "session.json"
    ScoreRegimeMtfABSessionReporter.export_json(recorder, path)
    loaded = ScoreRegimeMtfABSessionReporter.load_json(path)
    assert loaded.dominant_effect == "POSITIVE"


def test_export_does_not_mutate_recorder(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    _record(recorder)
    before = recorder.samples
    ScoreRegimeMtfABSessionReporter.export_json(recorder, tmp_path / "session.json")
    assert recorder.samples == before
