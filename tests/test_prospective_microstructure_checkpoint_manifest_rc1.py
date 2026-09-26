from __future__ import annotations

import json

import pytest

from tools.prospective_microstructure_checkpoint_manifest import (
    STATUS,
    VERSION,
    create_manifest,
    verify_manifest,
)


def _write(path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_create_manifest_locks_order_path_and_sha256(tmp_path):
    first = tmp_path / "session1.json"
    second = tmp_path / "session2.json"

    _write(first, '{"session":1}\n')
    _write(second, '{"session":2}\n')

    result = create_manifest(
        [first, second],
        protocol="TEST_CHECKPOINT",
    )

    assert result["version"] == VERSION
    assert result["status"] == STATUS
    assert result["protocol"] == "TEST_CHECKPOINT"
    assert result["session_count"] == 2

    assert [item["position"] for item in result["sessions"]] == [1, 2]
    assert result["sessions"][0]["path"] == str(first)
    assert result["sessions"][1]["path"] == str(second)

    assert len(result["sessions"][0]["sha256"]) == 64
    assert len(result["sessions"][1]["sha256"]) == 64
    assert (
        result["sessions"][0]["sha256"]
        != result["sessions"][1]["sha256"]
    )

    assert result["research_only"] is True
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["promotion_allowed"] is False


def test_verify_manifest_accepts_unchanged_files(tmp_path):
    first = tmp_path / "session1.json"
    second = tmp_path / "session2.json"

    _write(first, '{"session":1}\n')
    _write(second, '{"session":2}\n')

    manifest = create_manifest(
        [first, second],
        protocol="TEST_CHECKPOINT",
    )

    result = verify_manifest(manifest)

    assert result["status"] == "CHECKPOINT_VERIFIED"
    assert result["verified"] is True
    assert result["session_count"] == 2
    assert result["reasons"] == []

    assert all(
        item["matched"] is True
        for item in result["sessions"]
    )


def test_verify_manifest_detects_file_mutation(tmp_path):
    first = tmp_path / "session1.json"
    second = tmp_path / "session2.json"

    _write(first, '{"session":1}\n')
    _write(second, '{"session":2}\n')

    manifest = create_manifest(
        [first, second],
        protocol="TEST_CHECKPOINT",
    )

    _write(second, '{"session":2,"altered":true}\n')

    result = verify_manifest(manifest)

    assert result["status"] == "CHECKPOINT_MISMATCH"
    assert result["verified"] is False
    assert "SESSION_2:SHA256_MISMATCH" in result["reasons"]

    assert result["sessions"][0]["matched"] is True
    assert result["sessions"][1]["matched"] is False
    assert (
        result["sessions"][1]["reason"]
        == "SHA256_MISMATCH"
    )


def test_verify_manifest_detects_missing_file(tmp_path):
    session = tmp_path / "session.json"

    _write(session, '{"session":1}\n')

    manifest = create_manifest(
        [session],
        protocol="TEST_CHECKPOINT",
    )

    session.unlink()

    result = verify_manifest(manifest)

    assert result["status"] == "CHECKPOINT_MISMATCH"
    assert result["verified"] is False
    assert result["sessions"][0]["matched"] is False
    assert result["sessions"][0]["actual_sha256"] is None

    assert any(
        reason.startswith("SESSION_1:UNREADABLE:")
        for reason in result["reasons"]
    )


def test_create_manifest_rejects_empty_cohort():
    with pytest.raises(
        ValueError,
        match="at least one session path is required",
    ):
        create_manifest(
            [],
            protocol="TEST_CHECKPOINT",
        )


@pytest.mark.parametrize(
    "protocol",
    [
        "",
        "   ",
    ],
)
def test_create_manifest_rejects_empty_protocol(protocol):
    with pytest.raises(
        ValueError,
        match="protocol must be a non-empty string",
    ):
        create_manifest(
            ["unused.json"],
            protocol=protocol,
        )


def test_create_manifest_rejects_duplicate_path(tmp_path):
    session = tmp_path / "session.json"
    _write(session, '{"session":1}\n')

    with pytest.raises(
        ValueError,
        match="duplicate session path",
    ):
        create_manifest(
            [session, session],
            protocol="TEST_CHECKPOINT",
        )


def test_create_manifest_rejects_duplicate_sha256(tmp_path):
    first = tmp_path / "session1.json"
    second = tmp_path / "session2.json"

    same_content = '{"same":true}\n'

    _write(first, same_content)
    _write(second, same_content)

    with pytest.raises(
        ValueError,
        match="duplicate session sha256",
    ):
        create_manifest(
            [first, second],
            protocol="TEST_CHECKPOINT",
        )


def test_verify_rejects_changed_manifest_order(tmp_path):
    first = tmp_path / "session1.json"
    second = tmp_path / "session2.json"

    _write(first, '{"session":1}\n')
    _write(second, '{"session":2}\n')

    manifest = create_manifest(
        [first, second],
        protocol="TEST_CHECKPOINT",
    )

    manifest["sessions"][0]["position"] = 2
    manifest["sessions"][1]["position"] = 1

    result = verify_manifest(manifest)

    assert result["status"] == "MANIFEST_INVALID"
    assert result["verified"] is False
    assert "SESSION_ORDER_INVALID" in result["reasons"]


def test_verify_rejects_session_count_mutation(tmp_path):
    session = tmp_path / "session.json"
    _write(session, '{"session":1}\n')

    manifest = create_manifest(
        [session],
        protocol="TEST_CHECKPOINT",
    )

    manifest["session_count"] = 2

    result = verify_manifest(manifest)

    assert result["status"] == "MANIFEST_INVALID"
    assert result["verified"] is False
    assert "SESSION_COUNT_MISMATCH" in result["reasons"]


def test_verify_rejects_safety_flag_mutation(tmp_path):
    session = tmp_path / "session.json"
    _write(session, '{"session":1}\n')

    manifest = create_manifest(
        [session],
        protocol="TEST_CHECKPOINT",
    )

    manifest["score_influence_allowed"] = True

    result = verify_manifest(manifest)

    assert result["status"] == "MANIFEST_INVALID"
    assert result["verified"] is False
    assert (
        "SAFETY_FLAG_INVALID:score_influence_allowed"
        in result["reasons"]
    )


def test_manifest_json_roundtrip_is_verifiable(tmp_path):
    session = tmp_path / "session.json"
    manifest_path = tmp_path / "manifest.json"

    _write(session, '{"session":1}\n')

    manifest = create_manifest(
        [session],
        protocol="TEST_CHECKPOINT",
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    loaded = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    result = verify_manifest(loaded)

    assert result["status"] == "CHECKPOINT_VERIFIED"
    assert result["verified"] is True