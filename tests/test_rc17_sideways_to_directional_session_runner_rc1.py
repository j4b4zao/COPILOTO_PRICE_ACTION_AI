"""Synthetic orchestration only: the live capture entry point is always mocked."""
import hashlib
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools import rc17_sideways_to_directional_session_runner as runner


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "git_value", lambda *a: runner.BRANCH if a[0] == "branch" else runner.EXPECTED_HEAD)
    capture = Mock()
    evaluate = Mock(return_value={"session_classification": "NO_DIRECTIONAL_TRANSITION_OBSERVED"})
    monkeypatch.setattr(runner, "run_session", capture)
    monkeypatch.setattr(runner.evaluator, "evaluate", evaluate)
    def write_raw(count=1):
        paths = []
        for i in range(count):
            p = tmp_path / f"profit_rtd_rc54_3_2_WINV26_new{i}.json"
            p.write_text(json.dumps({"symbol": "SYNTHETIC_ONLY", "samples": []}))
            paths.append(p)
        return {"status": "COMPLETED", "output_path": str(paths[0]) if paths else None}
    capture.side_effect = lambda *a, **k: write_raw()
    args = dict(session_id=19, confirm_session_id=19, symbol="WINV26",
                requested_cycles=600, output_dir=tmp_path, date="20261003")
    return args, capture, evaluate, write_raw


def test_dry_run_no_capture_or_files(setup, tmp_path):
    args, capture, evaluate, _ = setup
    result = runner.run(**args)
    assert result["STATUS"] == "DRY_RUN_PASS"
    assert result["CAPTURE_CALL_COUNT"] == result["COLLECTOR_CALL_COUNT"] == 0
    capture.assert_not_called()
    evaluate.assert_not_called()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("change", [
    {"confirm_session_id": None}, {"confirm_session_id": 20},
    {"session_id": 18}, {"session_id": 24}, {"requested_cycles": 599},
    {"market_structure_observability_enabled": False}, {"symbol": ""},
    {"expected_head": "0" * 40},
])
def test_preflight_rejects_before_capture(setup, change):
    args, capture, evaluate, _ = setup
    result = runner.run(**{**args, **change}, execute_live=True)
    assert result["STATUS"] == "ABORT"
    capture.assert_not_called()
    evaluate.assert_not_called()


def test_bad_protocol_hash(setup, tmp_path):
    args, capture, evaluate, _ = setup
    protocol = tmp_path / "bad.json"
    protocol.write_text("{}")
    assert runner.run(**args, protocol_path=protocol, execute_live=True)["STATUS"] == "ABORT"
    capture.assert_not_called()
    evaluate.assert_not_called()


@pytest.mark.parametrize("count", [0, 2])
def test_ambiguous_raw(setup, count, tmp_path):
    args, capture, evaluate, write_raw = setup
    capture.side_effect = lambda *a, **k: write_raw(count)
    result = runner.run(**args, execute_live=True)
    assert result["STATUS"] == "ABORT"
    assert "ambiguity" in result["ERROR"]
    evaluate.assert_not_called()
    assert not list(tmp_path.glob("rc17_sideways*.json"))


def test_single_capture_exact_raw_and_no_next_session(setup, tmp_path):
    args, capture, evaluate, _ = setup
    old = tmp_path / "profit_rtd_rc54_3_2_WINV26_old.json"
    old.write_text("old synthetic fixture")
    os.utime(old, (2000000000, 2000000000))
    result = runner.run(**args, execute_live=True)
    capture.assert_called_once_with("WINV26", cycles=600, output_dir=str(tmp_path),
                                    market_structure_observability_enabled=True)
    raw = tmp_path / "profit_rtd_rc54_3_2_WINV26_new0.json"
    evaluate.assert_called_once_with(raw_path=raw, session_id=19,
                                    protocol_path=runner.ROOT / runner.validator.PROTOCOL_PATH)
    assert result["RAW_SHA256"] == hashlib.sha256(raw.read_bytes()).hexdigest()
    assert result["RAW_SIZE"] == raw.stat().st_size
    assert result["SESSION_NEXT_EXECUTED"] is False
    assert result["CAPTURE_CALL_COUNT"] == 1
    assert Path(result["RESULT_JSON"]).is_file()
    assert old.read_text() == "old synthetic fixture"
    assert "COLLECTOR_CALL_COUNT=1" in next(tmp_path.glob("saida_*.txt")).read_text()


@pytest.mark.parametrize("kind", ["result", "report"])
def test_existing_output_blocks_live_but_not_dry(setup, tmp_path, kind):
    args, capture, _, _ = setup
    name = ("rc17_sideways_to_directional_evolution_session19_rc1_20261003.json" if kind == "result"
            else "saida_rc17_sideways_to_directional_session19_rc1_20261003.txt")
    path = tmp_path / name
    path.write_text("preserve")
    assert runner.run(**args, execute_live=True)["STATUS"] == "ABORT"
    assert runner.run(**args)["STATUS"] == "DRY_RUN_PASS"
    capture.assert_not_called()
    assert path.read_text() == "preserve"


def test_capture_exception(setup, tmp_path):
    args, capture, evaluate, _ = setup
    capture.side_effect = RuntimeError("synthetic capture failure")
    result = runner.run(**args, execute_live=True)
    assert "synthetic capture failure" in result["ERROR"]
    evaluate.assert_not_called()
    assert "synthetic capture failure" in next(tmp_path.glob("saida_*.txt")).read_text()


def test_integrity_failure_preserved(setup):
    args, _, evaluate, _ = setup
    evaluate.return_value = {"session_classification": "CAPTURE_INTEGRITY_FAILURE",
                             "integrity": {"valid": False, "failures": ["observability absent"]}}
    result = runner.run(**args, execute_live=True)
    assert result["STATUS"] == result["SESSION_CLASSIFICATION"] == "CAPTURE_INTEGRITY_FAILURE"
    assert json.loads(Path(result["RESULT_JSON"]).read_text()) == evaluate.return_value


@pytest.mark.parametrize("failure", ["capture", "evaluator", "path", "protocol"])
def test_fail_closed_after_capture(setup, monkeypatch, tmp_path, failure):
    args, capture, evaluate, write_raw = setup
    if failure == "capture":
        capture.side_effect = lambda *a, **k: {"status": "FAILED"}
    elif failure == "evaluator":
        evaluate.side_effect = ValueError("synthetic evaluation failure")
    elif failure == "path":
        capture.side_effect = lambda *a, **k: {**write_raw(), "output_path": "wrong.json"}
    else:
        protocol = tmp_path / "protocol.json"
        protocol.write_bytes((runner.ROOT / runner.validator.PROTOCOL_PATH).read_bytes())
        args["protocol_path"] = protocol
        def mutate(*a, **k):
            result = write_raw()
            protocol.write_text("{}")
            return result
        capture.side_effect = mutate
    result = runner.run(**args, execute_live=True)
    assert result["STATUS"] == "ABORT"
    if failure != "evaluator":
        evaluate.assert_not_called()


def test_branch_and_validator_fail_closed(setup, monkeypatch):
    args, capture, _, _ = setup
    monkeypatch.setattr(runner, "git_value", lambda *a: "wrong")
    assert runner.run(**args, execute_live=True)["STATUS"] == "ABORT"
    capture.assert_not_called()


def test_validator_failure(setup, monkeypatch):
    args, capture, evaluate, _ = setup
    monkeypatch.setattr(runner.validator, "validate", Mock(side_effect=ValueError("validator failed")))
    assert runner.run(**args, execute_live=True)["STATUS"] == "ABORT"
    capture.assert_not_called()
    evaluate.assert_not_called()


def test_raw_mutation_aborts(setup):
    args, _, evaluate, _ = setup
    def mutate(**kwargs):
        kwargs["raw_path"].write_text("changed synthetic fixture")
        return {"session_classification": "NO_DIRECTIONAL_TRANSITION_OBSERVED"}
    evaluate.side_effect = mutate
    result = runner.run(**args, execute_live=True)
    assert result["STATUS"] == "ABORT"
    assert result["RESULT_JSON"] is None


def test_cli_dry_run(setup, capsys):
    args, capture, _, _ = setup
    assert runner.main(["--session-id", "19", "--confirm-session-id", "19",
                        "--symbol", "WINV26", "--requested-cycles", "600",
                        "--output-dir", str(args["output_dir"])]) == 0
    assert json.loads(capsys.readouterr().out)["CAPTURE_CALL_COUNT"] == 0
    capture.assert_not_called()


def test_protected_files_preserved(setup):
    names = ["analysis/market_structure.py", "analysis/price_action/price_action.py",
             "market_data/collector.py", "tools/profit_rtd_microstructure_prospective_session.py",
             "tools/profit_rtd_rc54_3_2_warmed_session.py", "tools/profit_rtd_rc54_3_2_warm_history_gate.py",
             str(runner.validator.PROTOCOL_PATH), "tools/rc17_sideways_to_directional_evolution_evaluator.py"]
    before = {name: (runner.ROOT / name).read_bytes() for name in names}
    runner.run(**setup[0])
    assert {name: (runner.ROOT / name).read_bytes() for name in names} == before


@pytest.mark.parametrize("session_id", [20, 21, 22, 23])
def test_explicit_future_ids(setup, session_id):
    args, capture, _, _ = setup
    result = runner.run(**{**args, "session_id": session_id, "confirm_session_id": session_id})
    assert result["STATUS"] == "DRY_RUN_PASS"
    capture.assert_not_called()
