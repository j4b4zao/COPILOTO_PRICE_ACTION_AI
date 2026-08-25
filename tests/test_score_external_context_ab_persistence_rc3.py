import json

import pytest

from analysis.replay.score_external_context_ab_recorder import (
    ScoreExternalContextABRecorder,
    ScoreExternalContextABSample,
)


def _sample(**overrides):
    data = {
        "baseline_total": 75.0,
        "adjusted_total": 76.6,
        "delta": 1.6,
        "baseline_grade": "B",
        "adjusted_grade": "B",
        "grade_changed": False,
        "baseline_valid": True,
        "adjusted_valid": True,
        "validity_changed": False,
        "bias": "BUY",
        "external_status": "ALIGNED",
        "external_risk": "RISK_ON",
        "external_bias": "BULLISH",
        "external_confidence": 0.8,
        "confidence_bucket": "HIGH",
        "adjustment": 1.6,
        "passive_only": True,
    }
    data.update(overrides)
    return ScoreExternalContextABSample(**data)


def test_sample_round_trip_dict():
    sample = _sample()
    assert ScoreExternalContextABSample.from_dict(sample.to_dict()) == sample


def test_add_sample_enforces_contract():
    recorder = ScoreExternalContextABRecorder()
    with pytest.raises(TypeError):
        recorder.add_sample({})


def test_jsonl_round_trip_preserves_samples(tmp_path):
    recorder = ScoreExternalContextABRecorder()
    recorder.add_sample(_sample())
    recorder.add_sample(_sample(external_status="CONFLICT", delta=-1.8, adjustment=-1.8))
    path = recorder.export_jsonl(tmp_path / "external.jsonl")
    loaded = ScoreExternalContextABRecorder.load_jsonl(path)
    assert loaded.samples == recorder.samples


def test_csv_export_writes_header_and_sample(tmp_path):
    recorder = ScoreExternalContextABRecorder()
    recorder.add_sample(_sample())
    text = recorder.export_csv(tmp_path / "external.csv").read_text(encoding="utf-8")
    assert "baseline_total" in text
    assert "RISK_ON" in text


def test_metrics_json_exports_summary_and_scenarios(tmp_path):
    recorder = ScoreExternalContextABRecorder()
    recorder.add_sample(_sample())
    payload = json.loads(recorder.export_metrics_json(tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert payload["summary"]["samples"] == 1
    assert payload["scenarios"]["by_risk"]["RISK_ON"]["samples"] == 1


def test_exports_create_parent_directories(tmp_path):
    recorder = ScoreExternalContextABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_jsonl(tmp_path / "nested" / "session.jsonl")
    assert path.exists()


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ScoreExternalContextABRecorder.load_jsonl(tmp_path / "missing.jsonl")


def test_invalid_jsonl_raises_with_line_number(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"ok": 1}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        ScoreExternalContextABRecorder.load_jsonl(path)


def test_load_respects_max_samples(tmp_path):
    path = tmp_path / "many.jsonl"
    lines = [json.dumps(_sample(baseline_total=float(i)).to_dict()) for i in range(5)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    recorder = ScoreExternalContextABRecorder.load_jsonl(path, max_samples=2)
    assert recorder.size == 2
    assert recorder.samples[0].baseline_total == 3.0
    assert recorder.samples[1].baseline_total == 4.0


def test_scenario_metrics_survive_reload(tmp_path):
    recorder = ScoreExternalContextABRecorder()
    recorder.add_sample(_sample())
    recorder.add_sample(_sample(
        bias="SELL",
        external_status="CONFLICT",
        external_risk="RISK_OFF",
        external_bias="BEARISH",
        external_confidence=0.9,
        confidence_bucket="HIGH",
        delta=-1.8,
        adjustment=-1.8,
    ))
    loaded = ScoreExternalContextABRecorder.load_jsonl(
        recorder.export_jsonl(tmp_path / "session.jsonl")
    )
    assert loaded.scenario(risk="RISK_ON")["positive_adjustments"] == 1
    assert loaded.scenario(risk="RISK_OFF")["negative_adjustments"] == 1
