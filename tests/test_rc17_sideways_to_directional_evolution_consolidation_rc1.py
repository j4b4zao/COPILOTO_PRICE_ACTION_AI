"""Fixed-cohort fixtures are synthetic evaluator JSONs in temporary directories."""
import json
from pathlib import Path

import pytest

from tools import rc17_sideways_to_directional_evolution_consolidation as c
from tools import rc17_sideways_to_directional_evolution_evaluator as evaluator


@pytest.fixture
def inputs(tmp_path):
    paths = []
    for sid in c.SESSION_IDS:
        raw = tmp_path / f"synthetic_raw_{sid}.json"
        raw.write_text(json.dumps(dict(symbol="SYNTHETIC_ONLY", samples=[], requested_cycles=600,
                                      analyzable_samples=0, skipped_cycles=600, collection_errors=0)))
        result = evaluator.evaluate(raw, sid, c.PROTOCOL_PATH)
        path = tmp_path / f"synthetic_result_{sid}.json"
        path.write_text(json.dumps(result))
        paths.append(path)
    return paths


def change(path, **fields):
    payload = json.loads(path.read_text())
    payload.update(fields)
    path.write_text(json.dumps(payload))


def event(path, direction, number=1):
    payload = json.loads(path.read_text())
    payload["session_classification"] = "DIRECTIONAL_TRANSITION_OBSERVED"
    payload["primary_event_count"] = number
    payload["transition_counts"]["SIDEWAYS_TO_" + direction] = number
    path.write_text(json.dumps(payload))


def test_five_without_transition(inputs):
    result = c.consolidate(inputs)
    assert result["cohort"] == dict(fixed_session_ids=[19,20,21,22,23],
                                   planned_sessions=5, completed_sessions=5, block_status="COMPLETE")
    assert result["descriptive_counts"] == dict(directional_transition_observed_sessions=0,
        no_directional_transition_observed_sessions=5, capture_integrity_failure_sessions=0, total_primary_events=0)


@pytest.mark.parametrize("direction", ["UP", "DOWN"])
def test_single_transition(inputs, direction):
    event(inputs[0], direction)
    result = c.consolidate(inputs)
    assert result["descriptive_counts"]["directional_transition_observed_sessions"] == 1
    assert result["transition_totals"]["SIDEWAYS_TO_" + direction] == 1


def test_multiple_events_and_all_totals(inputs):
    event(inputs[0], "UP", 2)
    event(inputs[1], "DOWN", 3)
    for index, path in enumerate(inputs):
        payload = json.loads(path.read_text())
        payload["transition_counts"]["SIDEWAYS_TO_SIDEWAYS"] = index
        payload["transition_counts"]["UP_TO_UP"] = index
        payload["unknown_transition_counts"]["UNKNOWN_TO_UP"] = index
        path.write_text(json.dumps(payload))
    result = c.consolidate(inputs)
    assert result["descriptive_counts"]["total_primary_events"] == 5
    assert result["descriptive_counts"]["directional_transition_observed_sessions"] == 2
    for key in c.TRANSITIONS:
        assert result["transition_totals"][key] == sum(json.loads(p.read_text())["transition_counts"][key] for p in inputs)
    assert result["unknown_transition_totals"]["UNKNOWN_TO_UP"] == 10
    assert "UNKNOWN_TO_UP" not in result["transition_totals"]


def test_integrity_failure_preserved(inputs):
    event(inputs[0], "UP", 2)
    change(inputs[0], session_classification="CAPTURE_INTEGRITY_FAILURE",
           integrity={"valid": False, "failures": ["synthetic absent observability"]})
    result = c.consolidate(inputs)
    counts = result["descriptive_counts"]
    assert counts["capture_integrity_failure_sessions"] == 1
    assert counts["no_directional_transition_observed_sessions"] == 4
    assert counts["directional_transition_observed_sessions"] == 0
    assert counts["total_primary_events"] == 2
    assert result["sessions"][0]["integrity"]["valid"] is False


@pytest.mark.parametrize("sid", [18, 24, True, "19", 20])
def test_invalid_or_duplicate_session(inputs, sid):
    change(inputs[0], session_id=sid)
    with pytest.raises(ValueError):
        c.consolidate(inputs)


def test_duplicate_path(inputs):
    with pytest.raises(ValueError):
        c.consolidate([inputs[0], *inputs[:4]])


def test_missing_session_function_and_cli(inputs, tmp_path):
    with pytest.raises(ValueError):
        c.consolidate(inputs[:4])
    args = sum(([f"--session{sid}-result", str(p)] for sid, p in zip(c.SESSION_IDS[:4], inputs)), [])
    with pytest.raises(SystemExit) as exc:
        c.main(args + ["--output-path", str(tmp_path / "synthetic_output.json")])
    assert exc.value.code == 2


@pytest.mark.parametrize("field,value", [
    ("evaluator_version", "wrong"), ("session_classification", "REPLICATED"),
    ("session_classification", "NOT_REPLICATED"), ("session_classification", "NOT_EVALUABLE"),
    ("primary_event_count", -1), ("primary_event_count", True),
])
def test_bad_identity_or_counts(inputs, field, value):
    change(inputs[0], **{field: value})
    with pytest.raises(ValueError):
        c.consolidate(inputs)


@pytest.mark.parametrize("field", list(c.FLAGS))
def test_research_flags(inputs, field):
    change(inputs[0], **{field: not c.FLAGS[field]})
    with pytest.raises(ValueError):
        c.consolidate(inputs)


@pytest.mark.parametrize("field,value", [("version", "wrong"), ("sha256", "0" * 64)])
def test_protocol_identity(inputs, field, value):
    payload = json.loads(inputs[0].read_text())
    payload["protocol"][field] = value
    change(inputs[0], protocol=payload["protocol"])
    with pytest.raises(ValueError):
        c.consolidate(inputs)


@pytest.mark.parametrize("field", ["sha256", "filename", "path", "size"])
def test_missing_raw_identity(inputs, field):
    raw = json.loads(inputs[0].read_text())["raw"]
    del raw[field]
    change(inputs[0], raw=raw)
    with pytest.raises(ValueError):
        c.consolidate(inputs)


def test_no_raw_reads_no_pooling_no_percentages_order(inputs, monkeypatch):
    permitted = {p.resolve() for p in inputs} | {Path(c.PROTOCOL_PATH).resolve()}
    read = Path.read_bytes
    def guarded(path):
        assert path.resolve() in permitted, "consolidator attempted to open raw"
        return read(path)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    result = c.consolidate(list(reversed(inputs)))
    assert [s["session_id"] for s in result["sessions"]] == list(c.SESSION_IDS)
    assert result["interpretation"]["raw_pooling"] is False
    forbidden = ("rate", "percent", "probability", "expectancy", "p_value", "confidence", "ranking", "score")
    def check(value):
        if isinstance(value, dict):
            for key, child in value.items():
                assert not any(word in key.lower() for word in forbidden)
                assert key != "samples"
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(result)


def test_preserve_per_session_counts(inputs):
    expected = [json.loads(p.read_text()) for p in inputs]
    result = c.consolidate(inputs)
    for payload, session in zip(expected, result["sessions"]):
        for key in session:
            assert session[key] == payload[key]


def test_cli_synthetic_output_no_overwrite(inputs, tmp_path):
    output = tmp_path / "synthetic_consolidation.json"
    args = sum(([f"--session{sid}-result", str(p)] for sid,p in zip(c.SESSION_IDS, inputs)), [])
    args += ["--output-path", str(output)]
    assert c.main(args) == 0
    before = output.read_bytes()
    assert c.main(args) == 2
    assert output.read_bytes() == before


def test_cli_slot_mismatch(inputs, tmp_path):
    paths = [inputs[1], inputs[0], *inputs[2:]]
    args = sum(([f"--session{sid}-result", str(p)] for sid,p in zip(c.SESSION_IDS, paths)), [])
    output = tmp_path / "synthetic_output.json"
    assert c.main(args + ["--output-path", str(output)]) == 2
    assert not output.exists()


def test_optional_transition_not_invented(inputs):
    payload = json.loads(inputs[0].read_text())
    del payload["transition_counts"]["UP_TO_UP"]
    change(inputs[0], transition_counts=payload["transition_counts"])
    result = c.consolidate(inputs)
    assert "UP_TO_UP" not in result["transition_totals"]


def test_protocol_file_fail_closed(inputs, tmp_path):
    protocol = tmp_path / "synthetic_bad_protocol.json"
    protocol.write_text("{}")
    with pytest.raises(ValueError):
        c.consolidate(inputs, protocol)
