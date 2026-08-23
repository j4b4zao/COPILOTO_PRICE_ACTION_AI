from analysis.replay.microstructure_confluence_replay_recorder import (
    MicrostructureConfluenceReplayRecorder,
    MicrostructureConfluenceReplaySample,
)


def _sample(independent=2, quality="MEDIUM", state="CONFIRMED", correlated=0, conflicts=0, confidence=0.7):
    return MicrostructureConfluenceReplaySample(
        state=state,
        direction="BUY",
        confluence_quality=quality,
        confidence=confidence,
        independent_evidence_count=independent,
        correlated_evidence_count=correlated,
        conflict_count=conflicts,
        price_action_bias="BUY",
        flow_direction="BUY",
        book_direction="BUY",
        book_available=True,
        book_correlated_with_delta=correlated > 0,
    )


def test_add_sample_and_group_by_quality():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample(quality="HIGH"))
    assert recorder.scenario_summary()["by_quality"]["HIGH"]["samples"] == 1


def test_group_by_independent_count():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample(independent=3))
    assert recorder.scenario_summary()["by_independent_evidence"]["3"]["samples"] == 1


def test_scenario_combined_filters():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample(independent=3, quality="HIGH"))
    recorder.add_sample(_sample(independent=2, quality="MEDIUM", correlated=1))
    result = recorder.scenario(independent=3, quality="HIGH", correlation="INDEPENDENT")
    assert result["samples"] == 1


def test_jsonl_roundtrip(tmp_path):
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample(independent=3, quality="HIGH"))
    path = recorder.export_jsonl(tmp_path / "microstructure.jsonl")
    loaded = MicrostructureConfluenceReplayRecorder()
    assert loaded.load_jsonl(path) == 1
    assert loaded.samples == recorder.samples


def test_csv_export(tmp_path):
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample())
    assert recorder.export_csv(tmp_path / "microstructure.csv").exists()


def test_metrics_json_export(tmp_path):
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample())
    text = recorder.export_metrics_json(tmp_path / "metrics.json").read_text(encoding="utf-8")
    assert '"scenarios"' in text


def test_invalid_jsonl_line_raises(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("{invalid}\n", encoding="utf-8")
    recorder = MicrostructureConfluenceReplayRecorder()
    try:
        recorder.load_jsonl(path)
    except ValueError as exc:
        assert "linha 1" in str(exc)
    else:
        raise AssertionError("ValueError esperado")


def test_max_samples_applies_on_load(tmp_path):
    source = MicrostructureConfluenceReplayRecorder()
    for _ in range(3):
        source.add_sample(_sample())
    path = source.export_jsonl(tmp_path / "session.jsonl")
    target = MicrostructureConfluenceReplayRecorder(max_samples=2)
    target.load_jsonl(path)
    assert target.size == 2


def test_from_dict_rejects_unknown_fields():
    payload = _sample().to_dict()
    payload["unknown"] = 1
    try:
        MicrostructureConfluenceReplaySample.from_dict(payload)
    except ValueError as exc:
        assert "unknown" in str(exc)
    else:
        raise AssertionError("ValueError esperado")


def test_conflict_group_is_preserved():
    recorder = MicrostructureConfluenceReplayRecorder()
    recorder.add_sample(_sample(state="CONFLICT", conflicts=1))
    assert recorder.scenario_summary()["by_conflict"]["WITH_CONFLICT"]["samples"] == 1
