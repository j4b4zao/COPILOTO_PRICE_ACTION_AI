from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_independent_session_comparison as comparison


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _checkpoint_payload() -> dict:
    sessions = []

    for position in range(1, 11):
        sessions.append(
            {
                "position": position,
                "path": f"session{position}.json",
                "sha256": f"{position:064x}",
            }
        )

    return {
        "version": (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "CHECKPOINT-MANIFEST"
        ),
        "status": "IDENTITY_LOCK_ONLY",
        "protocol": (
            "PROSPECTIVE_MICROSTRUCTURE_CONFLICT_"
            "10_SESSION_CHECKPOINT"
        ),
        "session_count": 10,
        "sessions": sessions,
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


def _audit_payload() -> dict:
    return {
        "version": (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "POST-SESSION-AUDIT"
        ),
        "status": "POST_SESSION_AUDIT_COMPLETED",
        "session_count": 1,
        "input_sessions": [
            {
                "position": 1,
                "path": "session11.json",
                "sha256": "a" * 64,
            }
        ],
        "pipeline": {
            "coverage": "COMPLETED",
            "episodes": "COMPLETED",
            "followthrough": "COMPLETED",
            "stratification": "COMPLETED",
            "stability": "COMPLETED",
        },
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


def test_safety_contract_is_passive():
    safety = comparison._safety()

    assert safety["research_only"] is True
    assert safety["observational_only"] is True
    assert safety["predictive_claim_allowed"] is False
    assert safety["score_influence_allowed"] is False
    assert safety["risk_influence_allowed"] is False
    assert safety["decision_influence_allowed"] is False
    assert safety["alert_influence_allowed"] is False
    assert safety["order_execution_allowed"] is False
    assert safety["promotion_allowed"] is False


def test_checkpoint_must_be_identity_locked():
    payload = _checkpoint_payload()
    payload["status"] = "CHECKPOINT_VERIFIED"

    with pytest.raises(
        ValueError,
        match="identity-locked",
    ):
        comparison._validate_checkpoint(payload)


def test_checkpoint_must_remain_ten_sessions():
    payload = _checkpoint_payload()
    payload["session_count"] = 11

    with pytest.raises(ValueError, match="10-session"):
        comparison._validate_checkpoint(payload)


def test_checkpoint_requires_ten_identities():
    payload = _checkpoint_payload()
    payload["sessions"].pop()

    with pytest.raises(
        ValueError,
        match="10 locked session identities",
    ):
        comparison._validate_checkpoint(payload)


def test_checkpoint_positions_must_be_ordered():
    payload = _checkpoint_payload()
    payload["sessions"][0]["position"] = 2

    with pytest.raises(
        ValueError,
        match="ordered 1..10",
    ):
        comparison._validate_checkpoint(payload)


def test_checkpoint_duplicate_sha_is_rejected():
    payload = _checkpoint_payload()

    payload["sessions"][1]["sha256"] = (
        payload["sessions"][0]["sha256"]
    )

    with pytest.raises(
        ValueError,
        match="duplicate checkpoint session sha256",
    ):
        comparison._validate_checkpoint(payload)


def test_independent_audit_must_be_single_session():
    payload = _audit_payload()
    payload["session_count"] = 2

    with pytest.raises(
        ValueError,
        match="single independent session",
    ):
        comparison._validate_independent_audit(payload)


def test_independent_audit_pipeline_must_be_complete():
    payload = _audit_payload()
    payload["pipeline"]["followthrough"] = "FAILED"

    with pytest.raises(
        ValueError,
        match="incomplete independent audit",
    ):
        comparison._validate_independent_audit(payload)


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
def test_unsafe_input_is_rejected(flag):
    payload = _audit_payload()

    if flag in (
        "research_only",
        "observational_only",
    ):
        payload[flag] = False
    else:
        payload[flag] = True

    with pytest.raises(
        ValueError,
        match="unsafe or missing flag",
    ):
        comparison._validate_safety(
            "independent audit",
            payload,
        )


def test_baseline_overlap_is_rejected():
    checkpoint = _checkpoint_payload()
    audit = _audit_payload()

    audit["input_sessions"][0]["sha256"] = (
        checkpoint["sessions"][0]["sha256"]
    )

    with pytest.raises(
        ValueError,
        match="already belongs to frozen baseline",
    ):
        comparison._validate_independence(
            checkpoint,
            audit,
        )


def test_build_report_preserves_checkpoint_boundary(
    tmp_path,
):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    audit_path = _write_json(
        tmp_path / "session11_audit.json",
        _audit_payload(),
    )

    report = comparison.build_report(
        checkpoint_path,
        audit_path,
    )

    assert (
        report["status"]
        == "INDEPENDENT_SESSION_COMPARISON_COMPLETED"
    )

    assert report["baseline"]["session_count"] == 10
    assert report["baseline"]["identity_count"] == 10
    assert report["independent"]["session_count"] == 1

    assert (
        report["architecture"]["baseline_mutated"]
        is False
    )

    assert (
        report["architecture"][
            "independent_appended_to_baseline"
        ]
        is False
    )

    assert (
        report["architecture"][
            "baseline_overlap_allowed"
        ]
        is False
    )

    assert (
        report["architecture"][
            "automatic_promotion_allowed"
        ]
        is False
    )

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["predictive_claim_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["promotion_allowed"] is False


def test_report_records_input_sha256(tmp_path):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    audit_path = _write_json(
        tmp_path / "audit.json",
        _audit_payload(),
    )

    report = comparison.build_report(
        checkpoint_path,
        audit_path,
    )

    assert len(report["baseline"]["sha256"]) == 64
    assert len(report["independent"]["sha256"]) == 64


def test_input_files_are_not_modified(tmp_path):
    checkpoint_path = _write_json(
        tmp_path / "checkpoint.json",
        _checkpoint_payload(),
    )

    audit_path = _write_json(
        tmp_path / "audit.json",
        _audit_payload(),
    )

    before_checkpoint = checkpoint_path.read_bytes()
    before_audit = audit_path.read_bytes()

    comparison.build_report(
        checkpoint_path,
        audit_path,
    )

    assert checkpoint_path.read_bytes() == before_checkpoint
    assert audit_path.read_bytes() == before_audit