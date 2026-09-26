from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_post_session_audit as audit


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_report(version: str) -> dict:
    return {
        "version": version,
        "status": "OK",
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
    }


def _patch_pipeline(monkeypatch):
    monkeypatch.setattr(
        audit,
        "coverage_report_paths",
        lambda paths: _safe_report("TEST-COVERAGE"),
    )

    monkeypatch.setattr(
        audit,
        "episode_report_paths",
        lambda paths: _safe_report("TEST-EPISODES"),
    )

    monkeypatch.setattr(
        audit,
        "followthrough_report_paths",
        lambda paths, horizons: _safe_report("TEST-FOLLOWTHROUGH"),
    )

    monkeypatch.setattr(
        audit,
        "stratification_report_file",
        lambda path: _safe_report("TEST-STRATIFICATION"),
    )

    monkeypatch.setattr(
        audit,
        "stability_build_report",
        lambda path: _safe_report("TEST-STABILITY"),
    )


def test_safety_contract_is_strict():
    safety = audit._safety()

    assert safety["research_only"] is True
    assert safety["observational_only"] is True

    assert safety["predictive_claim_allowed"] is False
    assert safety["score_influence_allowed"] is False
    assert safety["risk_influence_allowed"] is False
    assert safety["decision_influence_allowed"] is False
    assert safety["alert_influence_allowed"] is False
    assert safety["order_execution_allowed"] is False
    assert safety["promotion_allowed"] is False


def test_requires_explicit_session():
    with pytest.raises(ValueError, match="at least one explicit"):
        audit._validate_explicit_paths([])


def test_missing_session_fails_closed(tmp_path):
    missing = tmp_path / "missing.json"

    with pytest.raises(ValueError, match="not a readable file"):
        audit._validate_explicit_paths([missing])


def test_duplicate_path_is_rejected(tmp_path):
    session = _write_json(
        tmp_path / "session.json",
        {"sample": 1},
    )

    with pytest.raises(ValueError, match="duplicate session path"):
        audit._validate_explicit_paths(
            [session, session]
        )


def test_duplicate_sha_is_rejected(tmp_path):
    first = _write_json(
        tmp_path / "first.json",
        {"same": True},
    )

    second = tmp_path / "second.json"
    second.write_bytes(first.read_bytes())

    paths = audit._validate_explicit_paths(
        [first, second]
    )

    with pytest.raises(ValueError, match="duplicate session sha256"):
        audit._identity(paths)


@pytest.mark.parametrize(
    "flag",
    [
        "research_only",
        "observational_only",
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
    ],
)
def test_unsafe_or_missing_safety_flag_is_rejected(flag):
    payload = _safe_report("TEST")

    if flag in (
        "research_only",
        "observational_only",
    ):
        payload[flag] = False
    else:
        payload[flag] = True

    with pytest.raises(ValueError, match="unsafe or missing flag"):
        audit._validate_safety(
            "test-stage",
            payload,
        )


def test_missing_safety_flag_is_rejected():
    payload = _safe_report("TEST")
    payload.pop("score_influence_allowed")

    with pytest.raises(ValueError, match="unsafe or missing flag"):
        audit._validate_safety(
            "test-stage",
            payload,
        )


def test_input_sha_is_preserved(tmp_path, monkeypatch):
    _patch_pipeline(monkeypatch)

    session = _write_json(
        tmp_path / "session.json",
        {"immutable": True},
    )

    before = _sha256(session)

    report = audit.run_audit(
        [session],
        output_dir=tmp_path / "out",
        horizons=(1, 5, 10, 20),
    )

    after = _sha256(session)

    assert before == after

    assert (
        report["input_sessions"][0]["sha256"]
        == before
    )


def test_pipeline_completes_all_passive_stages(
    tmp_path,
    monkeypatch,
):
    _patch_pipeline(monkeypatch)

    session = _write_json(
        tmp_path / "session.json",
        {"session": 11},
    )

    report = audit.run_audit(
        [session],
        output_dir=tmp_path / "out",
        horizons=(1, 5, 10, 20),
    )

    assert report["status"] == "POST_SESSION_AUDIT_COMPLETED"

    assert report["pipeline"] == {
        "coverage": "COMPLETED",
        "episodes": "COMPLETED",
        "followthrough": "COMPLETED",
        "stratification": "COMPLETED",
        "stability": "COMPLETED",
    }

    assert report["architecture"]["session_selection"] == "EXPLICIT_ONLY"
    assert report["architecture"]["glob_discovery_allowed"] is False
    assert report["architecture"]["historical_checkpoint_mutated"] is False
    assert report["architecture"]["input_mutation_allowed"] is False

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["promotion_allowed"] is False


def test_followthrough_feeds_both_downstream_stages(
    tmp_path,
    monkeypatch,
):
    session = _write_json(
        tmp_path / "session.json",
        {"session": 11},
    )

    monkeypatch.setattr(
        audit,
        "coverage_report_paths",
        lambda paths: _safe_report("COVERAGE"),
    )

    monkeypatch.setattr(
        audit,
        "episode_report_paths",
        lambda paths: _safe_report("EPISODES"),
    )

    monkeypatch.setattr(
        audit,
        "followthrough_report_paths",
        lambda paths, horizons: _safe_report("FOLLOWTHROUGH"),
    )

    received = {}

    def fake_stratification(path):
        received["stratification"] = Path(path)
        return _safe_report("STRATIFICATION")

    def fake_stability(path):
        received["stability"] = Path(path)
        return _safe_report("STABILITY")

    monkeypatch.setattr(
        audit,
        "stratification_report_file",
        fake_stratification,
    )

    monkeypatch.setattr(
        audit,
        "stability_build_report",
        fake_stability,
    )

    audit.run_audit(
        [session],
        output_dir=tmp_path / "out",
    )

    assert (
        received["stratification"]
        == received["stability"]
    )

    assert (
        received["stratification"].name
        == "session_followthrough.json"
    )


def test_stage_failure_stops_pipeline(
    tmp_path,
    monkeypatch,
):
    session = _write_json(
        tmp_path / "session.json",
        {"session": 11},
    )

    monkeypatch.setattr(
        audit,
        "coverage_report_paths",
        lambda paths: _safe_report("COVERAGE"),
    )

    def fail_episode(paths):
        raise ValueError("controlled episode failure")

    monkeypatch.setattr(
        audit,
        "episode_report_paths",
        fail_episode,
    )

    called = {
        "followthrough": False,
    }

    def forbidden_followthrough(paths, horizons):
        called["followthrough"] = True
        return _safe_report("FOLLOWTHROUGH")

    monkeypatch.setattr(
        audit,
        "followthrough_report_paths",
        forbidden_followthrough,
    )

    with pytest.raises(
        ValueError,
        match="controlled episode failure",
    ):
        audit.run_audit(
            [session],
            output_dir=tmp_path / "out",
        )

    assert called["followthrough"] is False


def test_failure_payload_is_passive():
    payload = audit._failure_payload(
        ValueError("controlled")
    )

    assert payload["status"] == "POST_SESSION_AUDIT_FAILED"
    assert payload["error_type"] == "ValueError"

    assert payload["research_only"] is True
    assert payload["observational_only"] is True
    assert payload["predictive_claim_allowed"] is False
    assert payload["score_influence_allowed"] is False
    assert payload["risk_influence_allowed"] is False
    assert payload["decision_influence_allowed"] is False
    assert payload["alert_influence_allowed"] is False
    assert payload["order_execution_allowed"] is False
    assert payload["promotion_allowed"] is False