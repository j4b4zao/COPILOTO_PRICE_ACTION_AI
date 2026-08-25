import json

import pytest

from analysis.replay.score_order_flow_structure_ab_recorder import (
    ScoreOrderFlowStructureABRecorder,
    ScoreOrderFlowStructureABSample,
)


def _sample(**overrides):
    data = dict(
        baseline_total=75.0,
        adjusted_total=76.2,
        delta=1.2,
        baseline_grade="B",
        adjusted_grade="B",
        grade_changed=False,
        baseline_valid=True,
        adjusted_valid=True,
        validity_changed=False,
        bias="BUY",
        pattern_direction="BUY",
        structure_alignment="ALIGNED",
        structural_confidence=0.8,
        confidence_bucket="HIGH",
        adjustment=1.2,
        passive_only=True,
    )
    data.update(overrides)
    return ScoreOrderFlowStructureABSample(**data)


def test_sample_round_trip_dict():
    sample = _sample()
    restored = ScoreOrderFlowStructureABSample.from_dict(sample.to_dict())
    assert restored == sample


def test_unknown_sample_field_is_rejected():
    payload = _sample().to_dict()
    payload["unexpected"] = 1
    with pytest.raises(ValueError):
        ScoreOrderFlowStructureABSample.from_dict(payload)


def test_add_sample_validates_contract():
    recorder = ScoreOrderFlowStructureABRecorder()
    with pytest.raises(TypeError):
        recorder.add_sample(object())


def test_jsonl_round_trip_preserves_samples(tmp_path):
    source = ScoreOrderFlowStructureABRecorder()
    source.add_sample(_sample())
    source.add_sample(_sample(delta=-0.6, adjusted_total=74.4, structure_alignment="CONFLICT"))
    path = source.export_jsonl(tmp_path / "session.jsonl")

    restored = ScoreOrderFlowStructureABRecorder()
    loaded = restored.load_jsonl(path)
    assert loaded == 2
    assert restored.samples == source.samples


def test_csv_export_contains_header_and_sample(tmp_path):
    recorder = ScoreOrderFlowStructureABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_csv(tmp_path / "session.csv")
    text = path.read_text(encoding="utf-8")
    assert "structure_alignment" in text
    assert "ALIGNED" in text


def test_metrics_json_contains_summary_and_scenarios(tmp_path):
    recorder = ScoreOrderFlowStructureABRecorder()
    recorder.add_sample(_sample())
    path = recorder.export_metrics_json(tmp_path / "metrics.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["samples"] == 1
    assert payload["scenarios"]["by_alignment"]["ALIGNED"]["samples"] == 1


def test_export_creates_parent_directories(tmp_path):
    recorder = ScoreOrderFlowStructureABRecorder()
    path = recorder.export_jsonl(tmp_path / "nested" / "session.jsonl")
    assert path.exists()


def test_invalid_jsonl_line_is_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"baseline_total": 1}\nnot-json\n', encoding="utf-8")
    recorder = ScoreOrderFlowStructureABRecorder()
    with pytest.raises(ValueError):
        recorder.load_jsonl(path)


def test_max_samples_is_respected_when_loading(tmp_path):
    source = ScoreOrderFlowStructureABRecorder()
    source.add_sample(_sample(baseline_total=71.0))
    source.add_sample(_sample(baseline_total=72.0))
    source.add_sample(_sample(baseline_total=73.0))
    path = source.export_jsonl(tmp_path / "session.jsonl")

    restored = ScoreOrderFlowStructureABRecorder(max_samples=2)
    restored.load_jsonl(path)
    assert len(restored.samples) == 2
    assert restored.samples[0].baseline_total == 72.0


def test_scenarios_are_preserved_after_reload(tmp_path):
    source = ScoreOrderFlowStructureABRecorder()
    source.add_sample(_sample(structure_alignment="ALIGNED", confidence_bucket="HIGH"))
    source.add_sample(
        _sample(
            delta=-0.6,
            adjusted_total=74.4,
            structure_alignment="CONFLICT",
            structural_confidence=0.6,
            confidence_bucket="MEDIUM",
        )
    )
    path = source.export_jsonl(tmp_path / "session.jsonl")

    restored = ScoreOrderFlowStructureABRecorder()
    restored.load_jsonl(path)
    assert restored.scenario(alignment="ALIGNED")["samples"] == 1
    assert restored.scenario(alignment="CONFLICT", confidence="MEDIUM")["samples"] == 1
