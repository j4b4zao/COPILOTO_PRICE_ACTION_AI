import json

import pytest

from analysis.replay.score_order_flow_ab_recorder import (
    ScoreOrderFlowABRecorder,
    ScoreOrderFlowABSample,
)


def _sample(**overrides):
    payload = {
        "baseline_total": 75.0,
        "adjusted_total": 76.4,
        "delta": 1.4,
        "baseline_grade": "B",
        "adjusted_grade": "B",
        "grade_changed": False,
        "baseline_valid": True,
        "adjusted_valid": True,
        "validity_changed": False,
        "bias": "BUY",
        "order_flow_status": "ALIGNED",
        "flow_momentum": "ACCELERATING_BUY",
        "delta_persistence": 0.8,
        "delta_impulse_ratio": 0.55,
        "evidence_strength": 0.7,
        "strength_bucket": "HIGH",
        "adjustment": 1.4,
        "passive_only": True,
    }
    payload.update(overrides)
    return ScoreOrderFlowABSample(**payload)


def test_sample_round_trip_from_dict():
    sample = _sample()
    assert ScoreOrderFlowABSample.from_dict(sample.to_dict()) == sample


def test_sample_from_dict_rejects_unknown_fields():
    payload = _sample().to_dict()
    payload["unexpected"] = 1
    with pytest.raises(ValueError):
        ScoreOrderFlowABSample.from_dict(payload)


def test_add_sample_enforces_contract():
    recorder = ScoreOrderFlowABRecorder()
    with pytest.raises(TypeError):
        recorder.add_sample({"delta": 1.0})


def test_export_jsonl_and_load_round_trip(tmp_path):
    recorder = ScoreOrderFlowABRecorder()
    recorder.add_sample(_sample())
    recorder.add_sample(_sample(bias="SELL", order_flow_status="CONFLICT", delta=-1.4, adjustment=-1.4))
    path = recorder.export_jsonl(tmp_path / "session.jsonl")

    loaded = ScoreOrderFlowABRecorder()
    assert loaded.load_jsonl(path) == 2
    assert loaded.samples == recorder.samples


def test_export_csv_writes_header_and_rows(tmp_path):
    recorder = ScoreOrderFlowABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_csv(tmp_path / "session.csv")
    text = path.read_text(encoding="utf-8")
    assert "baseline_total" in text
    assert "ACCELERATING_BUY" in text


def test_export_metrics_json_contains_summary_and_scenarios(tmp_path):
    recorder = ScoreOrderFlowABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_metrics_json(tmp_path / "metrics.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["samples"] == 1
    assert payload["scenarios"]["by_momentum"]["ACCELERATING_BUY"]["samples"] == 1


def test_exports_create_parent_directories(tmp_path):
    recorder = ScoreOrderFlowABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_jsonl(tmp_path / "nested" / "deeper" / "session.jsonl")
    assert path.exists()


def test_load_jsonl_reports_invalid_line(tmp_path):
    path = tmp_path / "broken.jsonl"
    path.write_text('{"baseline_total": 75}\nnot-json\n', encoding="utf-8")
    recorder = ScoreOrderFlowABRecorder()
    with pytest.raises(ValueError, match="linha 2"):
        recorder.load_jsonl(path)


def test_load_jsonl_respects_max_samples(tmp_path):
    source = ScoreOrderFlowABRecorder()
    source.add_sample(_sample(delta=0.1))
    source.add_sample(_sample(delta=0.2))
    source.add_sample(_sample(delta=0.3))
    path = source.export_jsonl(tmp_path / "session.jsonl")

    target = ScoreOrderFlowABRecorder(max_samples=2)
    assert target.load_jsonl(path) == 3
    assert target.size == 2
    assert [sample.delta for sample in target.samples] == [0.2, 0.3]


def test_reload_preserves_scenario_metrics(tmp_path):
    recorder = ScoreOrderFlowABRecorder()
    recorder.add_sample(_sample())
    recorder.add_sample(
        _sample(
            bias="SELL",
            order_flow_status="CONFLICT",
            flow_momentum="PERSISTENT_BUY",
            delta=-1.0,
            evidence_strength=0.5,
            strength_bucket="MEDIUM",
            adjustment=-1.0,
        )
    )
    before = recorder.scenario_summary()
    path = recorder.export_jsonl(tmp_path / "session.jsonl")

    loaded = ScoreOrderFlowABRecorder()
    loaded.load_jsonl(path)
    after = loaded.scenario_summary()

    assert after["by_status"] == before["by_status"]
    assert after["by_momentum"] == before["by_momentum"]
    assert after["by_strength"] == before["by_strength"]
