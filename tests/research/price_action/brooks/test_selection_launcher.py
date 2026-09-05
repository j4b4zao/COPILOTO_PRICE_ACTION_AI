import json
from datetime import datetime

import tools.profit_rtd_brooks_selection_launcher as launcher


def _runner_result(symbol, sessions):
    return {
        "runner": "BROOKS_SELECTION_RUNNER_V1",
        "mode": "SELECTION",
        "symbol": symbol,
        "requested_sessions": sessions,
        "completed_runs": sessions,
        "produced_session_files": sessions,
        "runs": [],
        "manifest": {
            "manifest": "BROOKS_SELECTION_SESSION_MANIFEST_V1",
            "mode": "SELECTION",
            "eligible_sessions": sessions,
            "rejected_sessions": 0,
            "selection_cutoff": "2026-09-08T10:00:00",
            "promotion_allowed": False,
            "hypothesis_freeze_allowed": False,
        },
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "oos_execution_allowed": False,
    }


def test_report_path_is_deterministic_and_sanitized(tmp_path):
    path = launcher.build_report_path(
        "winv26!",
        report_dir=tmp_path,
        now=datetime(2026, 9, 8, 9, 30, 1),
    )
    assert path.name == "brooks_selection_WINV26_20260908_093001.json"


def test_launch_calls_selection_runner_and_writes_report(tmp_path, monkeypatch):
    calls = {}

    def fake_run(symbol, **kwargs):
        calls["symbol"] = symbol
        calls.update(kwargs)
        return _runner_result(symbol, kwargs["sessions"])

    monkeypatch.setattr(launcher, "run_selection", fake_run)
    result = launcher.launch_selection(
        "WINV26",
        sessions=2,
        cycles=10,
        interval=0.0,
        max_warmup_cycles=20,
        output_dir=tmp_path / "sessions",
        report_dir=tmp_path / "reports",
        now=datetime(2026, 9, 8, 9, 30, 1),
    )

    assert calls["symbol"] == "WINV26"
    assert calls["sessions"] == 2
    assert calls["cycles"] == 10
    assert result["launcher"] == "BROOKS_SELECTION_LAUNCHER_V1"
    report = json.loads((tmp_path / "reports" / "brooks_selection_WINV26_20260908_093001.json").read_text(encoding="utf-8"))
    assert report["manifest"]["eligible_sessions"] == 2


def test_launch_preserves_selection_only_safety(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "run_selection", lambda symbol, **kwargs: _runner_result(symbol, kwargs["sessions"]))
    result = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        now=datetime(2026, 9, 8, 9, 30, 1),
    )
    assert result["mode"] == "SELECTION"
    assert result["research_only"] is True
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["oos_execution_allowed"] is False


def test_main_returns_zero_when_all_sessions_are_eligible(tmp_path, monkeypatch):
    monkeypatch.setattr(
        launcher,
        "launch_selection",
        lambda *args, **kwargs: {
            **_runner_result("WINV26", 1),
            "launcher": "BROOKS_SELECTION_LAUNCHER_V1",
            "report_path": str(tmp_path / "report.json"),
        },
    )
    assert launcher.main(["WINV26"]) == 0


def test_main_returns_two_when_manifest_rejects_session(tmp_path, monkeypatch):
    result = _runner_result("WINV26", 1)
    result["manifest"]["eligible_sessions"] = 0
    result["manifest"]["rejected_sessions"] = 1
    result["launcher"] = "BROOKS_SELECTION_LAUNCHER_V1"
    result["report_path"] = str(tmp_path / "report.json")
    monkeypatch.setattr(launcher, "launch_selection", lambda *args, **kwargs: result)
    assert launcher.main(["WINV26"]) == 2
