import csv
import json

import pytest

from analysis.replay.score_regime_mtf_ab_recorder import (
    ScoreRegimeMtfABRecorder,
    ScoreRegimeMtfABSample,
)


def _sample(**overrides):
    payload = dict(
        baseline_total=75.0,
        adjusted_total=78.0,
        delta=3.0,
        baseline_grade="B",
        adjusted_grade="B",
        grade_changed=False,
        baseline_valid=True,
        adjusted_valid=True,
        validity_changed=False,
        bias="BUY",
        mtf_alignment="BUY",
        regime_context="TREND_UP",
        regime_compatible=True,
        adjustment=3.0,
        passive_only=True,
    )
    payload.update(overrides)
    return ScoreRegimeMtfABSample(**payload)


def test_export_jsonl_and_load_round_trip(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_jsonl(tmp_path / "session.jsonl")
    loaded = ScoreRegimeMtfABRecorder.load_jsonl(path)
    assert loaded.samples == recorder.samples


def test_export_csv_writes_header_and_row(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_csv(tmp_path / "session.csv")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["bias"] == "BUY"
    assert rows[0]["regime_context"] == "TREND_UP"


def test_export_metrics_json_contains_summary_and_scenarios(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_metrics_json(tmp_path / "metrics.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["samples"] == 1
    assert payload["scenarios"]["by_regime"]["TREND_UP"]["samples"] == 1


def test_exports_create_parent_directories(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    recorder.add_sample(_sample())
    assert recorder.export_jsonl(tmp_path / "a" / "b" / "session.jsonl").exists()
    assert recorder.export_csv(tmp_path / "c" / "d" / "session.csv").exists()
    assert recorder.export_metrics_json(tmp_path / "e" / "f" / "metrics.json").exists()


def test_empty_recorder_exports_valid_files(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    jsonl = recorder.export_jsonl(tmp_path / "empty.jsonl")
    csv_path = recorder.export_csv(tmp_path / "empty.csv")
    metrics = recorder.export_metrics_json(tmp_path / "empty_metrics.json")
    assert jsonl.read_text(encoding="utf-8") == ""
    assert "baseline_total" in csv_path.read_text(encoding="utf-8")
    assert json.loads(metrics.read_text(encoding="utf-8"))["summary"]["samples"] == 0


def test_load_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ScoreRegimeMtfABRecorder.load_jsonl(tmp_path / "missing.jsonl")


def test_load_invalid_jsonl_raises(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{bad json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSONL at line 1"):
        ScoreRegimeMtfABRecorder.load_jsonl(path)


def test_load_non_object_jsonl_raises(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="object expected"):
        ScoreRegimeMtfABRecorder.load_jsonl(path)


def test_load_respects_max_samples(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    recorder.add_sample(_sample(bias="BUY"))
    recorder.add_sample(_sample(bias="SELL", mtf_alignment="SELL", regime_context="TREND_DOWN"))
    path = recorder.export_jsonl(tmp_path / "session.jsonl")
    loaded = ScoreRegimeMtfABRecorder.load_jsonl(path, max_samples=1)
    assert loaded.size == 1
    assert loaded.samples[0].bias == "SELL"


def test_scenario_metrics_survive_round_trip(tmp_path):
    recorder = ScoreRegimeMtfABRecorder()
    recorder.add_sample(_sample())
    recorder.add_sample(
        _sample(
            adjusted_total=72.0,
            delta=-3.0,
            bias="SELL",
            mtf_alignment="CONFLICT_REGIME",
            regime_context="TREND_UP",
            regime_compatible=False,
            adjustment=-3.0,
        )
    )
    path = recorder.export_jsonl(tmp_path / "session.jsonl")
    loaded = ScoreRegimeMtfABRecorder.load_jsonl(path)
    assert loaded.summary()["average_delta"] == 0.0
    assert loaded.scenario(alignment="CONFLICT_REGIME")["negative_adjustments"] == 1
