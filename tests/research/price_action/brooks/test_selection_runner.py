import json
from pathlib import Path

import pytest

import tools.profit_rtd_brooks_selection_runner as runner


def _write_session(path, start="2026-09-08T09:00:00", end="2026-09-08T09:05:00"):
    payload = {
        "data_ready": True,
        "samples": [
            {"candle_evidence": {"timestamp": start}},
            {"candle_evidence": {"timestamp": end}},
        ],
        "brooks_first_pullback_capture": True,
        "brooks_major_reversal_context_capture": True,
        "brooks_wedge_three_pushes_capture": True,
        "brooks_trading_range_capture": True,
        "brooks_predictive_claim_allowed": False,
        "brooks_score_influence_allowed": False,
        "brooks_risk_influence_allowed": False,
        "brooks_decision_influence_allowed": False,
        "brooks_alert_influence_allowed": False,
        "brooks_order_execution_allowed": False,
    }
    Path(path).write_text(json.dumps(payload), encoding="utf-8")


def test_rejects_zero_sessions():
    with pytest.raises(ValueError, match="sessions must be >= 1"):
        runner.run_selection("WINV26", sessions=0)


def test_runs_single_session_and_builds_manifest(tmp_path, monkeypatch):
    session_path = tmp_path / "session.json"
    _write_session(session_path)

    def fake_run(*args, **kwargs):
        return {
            "status": "COMPLETED",
            "data_ready": True,
            "analyzable_samples": 2,
            "collection_errors": 0,
            "output_path": str(session_path),
            "reasons": [],
        }

    monkeypatch.setattr(runner.warmed, "run_warmed_session", fake_run)
    result = runner.run_selection("WINV26", output_dir=tmp_path)

    assert result["requested_sessions"] == 1
    assert result["completed_runs"] == 1
    assert result["produced_session_files"] == 1
    assert result["manifest"]["eligible_sessions"] == 1
    assert result["mode"] == "SELECTION"


def test_multiple_sessions_are_forwarded(tmp_path, monkeypatch):
    paths = []
    for index, hour in enumerate((9, 10)):
        path = tmp_path / f"session_{index}.json"
        _write_session(path, f"2026-09-08T{hour:02d}:00:00", f"2026-09-08T{hour:02d}:05:00")
        paths.append(path)
    calls = []

    def fake_run(*args, **kwargs):
        path = paths[len(calls)]
        calls.append(kwargs)
        return {"status": "COMPLETED", "data_ready": True, "analyzable_samples": 2, "collection_errors": 0, "output_path": str(path), "reasons": []}

    monkeypatch.setattr(runner.warmed, "run_warmed_session", fake_run)
    result = runner.run_selection("WINV26", sessions=2, cycles=123, interval=0.5, max_warmup_cycles=999, output_dir=tmp_path)

    assert len(calls) == 2
    assert all(call["cycles"] == 123 for call in calls)
    assert all(call["interval"] == 0.5 for call in calls)
    assert all(call["max_warmup_cycles"] == 999 for call in calls)
    assert result["manifest"]["eligible_sessions"] == 2


def test_missing_output_path_is_not_manifested(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.warmed, "run_warmed_session", lambda *a, **k: {"status": "FAILED", "data_ready": False, "collection_errors": 1, "reasons": ["TEST_FAILURE"]})
    result = runner.run_selection("WINV26", output_dir=tmp_path)
    assert result["produced_session_files"] == 0
    assert result["manifest"]["eligible_sessions"] == 0


def test_runner_never_allows_oos_or_promotion(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.warmed, "run_warmed_session", lambda *a, **k: {"status": "FAILED", "reasons": []})
    result = runner.run_selection("WINV26", output_dir=tmp_path)
    assert result["oos_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False


def test_sleeper_is_forwarded(tmp_path, monkeypatch):
    seen = {}
    marker = object()

    def fake_run(*args, **kwargs):
        seen.update(kwargs)
        return {"status": "FAILED", "reasons": []}

    monkeypatch.setattr(runner.warmed, "run_warmed_session", fake_run)
    runner.run_selection("WINV26", output_dir=tmp_path, sleeper=marker)
    assert seen["sleeper"] is marker
