import json

import pytest

from analysis.replay.score_book_depth_ab_recorder import (
    ScoreBookDepthABRecorder,
    ScoreBookDepthABSample,
)


def _sample(**overrides):
    data = dict(
        baseline_total=80.0,
        adjusted_total=80.8,
        delta=0.8,
        baseline_grade="A",
        adjusted_grade="A",
        grade_changed=False,
        baseline_valid=True,
        adjusted_valid=True,
        validity_changed=False,
        bias="BUY",
        status="ALIGNED",
        pressure="BID_DOMINANT",
        confidence=0.8,
        confidence_bucket="HIGH",
        duplicate_evidence_risk=False,
        correlation_bucket="INDEPENDENT",
        correlation_factor=1.0,
        effective_strength=0.8,
        adjustment=0.8,
        passive_only=True,
    )
    data.update(overrides)
    return ScoreBookDepthABSample(**data)


def test_round_trip_jsonl(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_jsonl(tmp_path / "session.jsonl")
    restored = ScoreBookDepthABRecorder()
    assert restored.load_jsonl(path) == 1
    assert restored.samples == recorder.samples


def test_export_csv(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_csv(tmp_path / "session.csv")
    text = path.read_text(encoding="utf-8")
    assert "baseline_total" in text
    assert "BID_DOMINANT" in text


def test_export_metrics_json(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_metrics_json(tmp_path / "metrics.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["samples"] == 1
    assert payload["scenarios"]["by_status"]["ALIGNED"]["samples"] == 1


def test_exports_create_parent_directories(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_jsonl(tmp_path / "nested" / "session.jsonl")
    assert path.exists()


def test_wrong_extension_is_rejected(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    with pytest.raises(ValueError):
        recorder.export_jsonl(tmp_path / "session.txt")


def test_missing_jsonl_raises(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    with pytest.raises(FileNotFoundError):
        recorder.load_jsonl(tmp_path / "missing.jsonl")


def test_invalid_jsonl_reports_line(tmp_path):
    path = tmp_path / "invalid.jsonl"
    path.write_text('{"baseline_total": 80}\nnot-json\n', encoding="utf-8")
    recorder = ScoreBookDepthABRecorder()
    with pytest.raises(ValueError, match="linha 2"):
        recorder.load_jsonl(path)


def test_max_samples_is_preserved_on_load(tmp_path):
    source = ScoreBookDepthABRecorder()
    source.add_sample(_sample(delta=0.1, adjusted_total=80.1))
    source.add_sample(_sample(delta=0.2, adjusted_total=80.2))
    source.add_sample(_sample(delta=0.3, adjusted_total=80.3))
    path = source.export_jsonl(tmp_path / "session.jsonl")
    restored = ScoreBookDepthABRecorder(max_samples=2)
    restored.load_jsonl(path)
    assert restored.size == 2
    assert [s.delta for s in restored.samples] == [0.2, 0.3]


def test_scenarios_survive_reload(tmp_path):
    recorder = ScoreBookDepthABRecorder()
    recorder.add_sample(_sample())
    recorder.add_sample(_sample(status="CONFLICT", pressure="ASK_DOMINANT", bias="SELL", confidence=0.5, confidence_bucket="MEDIUM", duplicate_evidence_risk=True, correlation_bucket="CORRELATED", correlation_factor=0.35, effective_strength=0.175, adjustment=-0.175, adjusted_total=79.825, delta=-0.175))
    path = recorder.export_jsonl(tmp_path / "session.jsonl")
    restored = ScoreBookDepthABRecorder()
    restored.load_jsonl(path)
    scenarios = restored.scenario_summary()
    assert scenarios["by_status"]["ALIGNED"]["samples"] == 1
    assert scenarios["by_status"]["CONFLICT"]["samples"] == 1
    assert scenarios["by_correlation"]["CORRELATED"]["samples"] == 1


def test_from_dict_rejects_unknown_fields():
    payload = _sample().to_dict()
    payload["unknown"] = True
    with pytest.raises(ValueError):
        ScoreBookDepthABSample.from_dict(payload)
