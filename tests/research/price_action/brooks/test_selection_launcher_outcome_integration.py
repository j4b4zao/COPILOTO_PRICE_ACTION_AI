from __future__ import annotations

import json

import tools.profit_rtd_brooks_selection_launcher as launcher


def _runner_result(*, produced=1, requested=1, eligible=1, rejected=0, mode="SELECTION"):
    return {
        "mode": mode,
        "symbol": "WINV26",
        "requested_sessions": requested,
        "produced_session_files": produced,
        "manifest": {
            "eligible_sessions": eligible,
            "rejected_sessions": rejected,
            "selection_cutoff": None,
        },
    }


def test_launcher_embeds_valid_selection_outcome(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "run_selection", lambda *args, **kwargs: _runner_result())

    result = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        output_dir=tmp_path / "sessions",
        sleeper=lambda _: None,
    )

    outcome = result["selection_outcome"]
    assert outcome["status"] == "VALID_SELECTION"
    assert outcome["counts_as_selection_evidence"] is True
    assert outcome["counts_as_oos_evidence"] is False


def test_launcher_embeds_no_valid_source_outcome(monkeypatch, tmp_path):
    monkeypatch.setattr(
        launcher,
        "run_selection",
        lambda *args, **kwargs: _runner_result(produced=0, eligible=0),
    )

    result = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        output_dir=tmp_path / "sessions",
        sleeper=lambda _: None,
    )

    outcome = result["selection_outcome"]
    assert outcome["status"] == "NO_VALID_SOURCE"
    assert outcome["counts_as_selection_evidence"] is False
    assert outcome["retry_when_real_source_active"] is True


def test_launcher_embeds_rejected_outcome(monkeypatch, tmp_path):
    monkeypatch.setattr(
        launcher,
        "run_selection",
        lambda *args, **kwargs: _runner_result(produced=1, eligible=0, rejected=1),
    )

    result = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        output_dir=tmp_path / "sessions",
        sleeper=lambda _: None,
    )

    assert result["selection_outcome"]["status"] == "REJECTED"
    assert result["selection_outcome"]["counts_as_selection_evidence"] is False


def test_launcher_persists_outcome_inside_json(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "run_selection", lambda *args, **kwargs: _runner_result())

    result = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        output_dir=tmp_path / "sessions",
        sleeper=lambda _: None,
    )

    payload = json.loads((tmp_path / result["report_path"].split("\\")[-1]).read_text(encoding="utf-8")) if "\\" in result["report_path"] else json.loads(__import__("pathlib").Path(result["report_path"]).read_text(encoding="utf-8"))
    assert payload["selection_outcome"]["status"] == "VALID_SELECTION"
    assert payload["selection_outcome"]["predictive_claim_allowed"] is False
    assert payload["selection_outcome"]["order_execution_allowed"] is False


def test_main_returns_zero_for_no_valid_source(monkeypatch, tmp_path):
    monkeypatch.setattr(
        launcher,
        "run_selection",
        lambda *args, **kwargs: _runner_result(produced=0, eligible=0),
    )

    code = launcher.main([
        "WINV26",
        "--report-dir",
        str(tmp_path),
        "--output-dir",
        str(tmp_path / "sessions"),
    ])
    assert code == 0


def test_main_returns_two_for_rejected(monkeypatch, tmp_path):
    monkeypatch.setattr(
        launcher,
        "run_selection",
        lambda *args, **kwargs: _runner_result(produced=1, eligible=0, rejected=1),
    )

    code = launcher.main([
        "WINV26",
        "--report-dir",
        str(tmp_path),
        "--output-dir",
        str(tmp_path / "sessions"),
    ])
    assert code == 2


def test_embedded_outcome_preserves_operational_isolation(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "run_selection", lambda *args, **kwargs: _runner_result())

    outcome = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        output_dir=tmp_path / "sessions",
        sleeper=lambda _: None,
    )["selection_outcome"]

    for flag in (
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
        "hypothesis_freeze_allowed",
    ):
        assert outcome[flag] is False


def test_embedded_outcome_never_counts_as_oos(monkeypatch, tmp_path):
    monkeypatch.setattr(launcher, "run_selection", lambda *args, **kwargs: _runner_result())

    outcome = launcher.launch_selection(
        "WINV26",
        report_dir=tmp_path,
        output_dir=tmp_path / "sessions",
        sleeper=lambda _: None,
    )["selection_outcome"]

    assert outcome["counts_as_oos_evidence"] is False
