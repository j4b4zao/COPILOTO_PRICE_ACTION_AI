from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from tools.prospective_microstructure_session11_readiness import (
    CHECKPOINT_PROTOCOL,
    CHECKPOINT_SAFETY,
    CHECKPOINT_STATUS,
    CHECKPOINT_VERSION,
    EXPECTED_ADMISSION,
    EXPECTED_ANALYSIS,
    EXPECTED_CHECKPOINT_GIT_COMMIT,
    EXPECTED_CHECKPOINT_REFERENCE,
    EXPECTED_PARAMETERS,
    EXPECTED_RUNNER,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    VERIFICATION_STATUS,
    _validate_checkpoint,
    _validate_protocol,
    _validate_verification,
    build_report,
)


def _write(
    path: Path,
    payload: dict,
) -> Path:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _protocol() -> dict:
    return {
        "version": PROTOCOL_VERSION,
        "protocol": PROTOCOL_NAME,
        "checkpoint_reference": (
            EXPECTED_CHECKPOINT_REFERENCE
        ),
        "checkpoint_git_commit": (
            EXPECTED_CHECKPOINT_GIT_COMMIT
        ),
        "session_number": 11,
        "symbol": "WINV26",
        "runner": EXPECTED_RUNNER,
        "runner_parameters": copy.deepcopy(
            EXPECTED_PARAMETERS
        ),
        "admission_policy": copy.deepcopy(
            EXPECTED_ADMISSION
        ),
        "analysis_policy": copy.deepcopy(
            EXPECTED_ANALYSIS
        ),
    }


def _checkpoint() -> dict:
    sessions = []

    for position in range(1, 11):
        sessions.append(
            {
                "position": position,
                "path": (
                    "data\\profit_rtd_rc54_3_2\\"
                    "profit_rtd_rc54_3_2_WINV26_"
                    f"202609{position:02d}_120000.json"
                ),
                "sha256": f"{position:064x}",
            }
        )

    return {
        "version": CHECKPOINT_VERSION,
        "status": CHECKPOINT_STATUS,
        "protocol": CHECKPOINT_PROTOCOL,
        "session_count": 10,
        "sessions": sessions,
        **copy.deepcopy(CHECKPOINT_SAFETY),
    }


def _verification(
    checkpoint: dict | None = None,
) -> dict:
    if checkpoint is None:
        checkpoint = _checkpoint()

    sessions = []

    for session in checkpoint["sessions"]:
        sessions.append(
            {
                "position": session["position"],
                "path": session["path"],
                "expected_sha256": session["sha256"],
                "actual_sha256": session["sha256"],
                "matched": True,
                "reason": None,
            }
        )

    return {
        "version": CHECKPOINT_VERSION,
        "status": VERIFICATION_STATUS,
        "verified": True,
        "protocol": CHECKPOINT_PROTOCOL,
        "session_count": 10,
        "sessions": sessions,
        "reasons": [],
        **copy.deepcopy(CHECKPOINT_SAFETY),
    }


def test_protocol_contract_passes() -> None:
    _validate_protocol(
        _protocol()
    )


def test_checkpoint_contract_passes() -> None:
    _validate_checkpoint(
        _checkpoint()
    )


def test_verification_contract_passes() -> None:
    checkpoint = _checkpoint()

    _validate_verification(
        _verification(checkpoint),
        checkpoint,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_number", 12),
        ("symbol", "WDO"),
        ("runner", "other.runner"),
        ("checkpoint_git_commit", "deadbeef"),
    ],
)
def test_protocol_identity_change_fails(
    field: str,
    value,
) -> None:
    payload = _protocol()
    payload[field] = value

    with pytest.raises(ValueError):
        _validate_protocol(payload)


def test_runner_parameter_change_fails() -> None:
    payload = _protocol()
    payload["runner_parameters"][
        "cycles"
    ] = 601

    with pytest.raises(ValueError):
        _validate_protocol(payload)


def test_extra_runner_parameter_fails() -> None:
    payload = _protocol()
    payload["runner_parameters"][
        "unexpected"
    ] = True

    with pytest.raises(ValueError):
        _validate_protocol(payload)


def test_admission_change_fails() -> None:
    payload = _protocol()
    payload["admission_policy"][
        "fail_closed"
    ] = False

    with pytest.raises(ValueError):
        _validate_protocol(payload)


def test_analysis_change_fails() -> None:
    payload = _protocol()
    payload["analysis_policy"][
        "score_influence_allowed"
    ] = True

    with pytest.raises(ValueError):
        _validate_protocol(payload)


def test_checkpoint_count_change_fails() -> None:
    payload = _checkpoint()
    payload["session_count"] = 11

    with pytest.raises(ValueError):
        _validate_checkpoint(payload)


def test_checkpoint_identity_count_change_fails() -> None:
    payload = _checkpoint()
    payload["sessions"].pop()

    with pytest.raises(ValueError):
        _validate_checkpoint(payload)


def test_checkpoint_position_change_fails() -> None:
    payload = _checkpoint()
    payload["sessions"][0][
        "position"
    ] = 2

    with pytest.raises(ValueError):
        _validate_checkpoint(payload)


def test_checkpoint_duplicate_hash_fails() -> None:
    payload = _checkpoint()

    payload["sessions"][1][
        "sha256"
    ] = payload["sessions"][0]["sha256"]

    with pytest.raises(ValueError):
        _validate_checkpoint(payload)


@pytest.mark.parametrize(
    "field",
    list(CHECKPOINT_SAFETY),
)
def test_checkpoint_safety_change_fails(
    field: str,
) -> None:
    payload = _checkpoint()

    payload[field] = not CHECKPOINT_SAFETY[
        field
    ]

    with pytest.raises(ValueError):
        _validate_checkpoint(payload)


def test_verification_status_change_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["status"] = "IDENTITY_LOCK_ONLY"

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_verified_false_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["verified"] = False

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_session_count_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["session_count"] = 9

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_identity_count_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"].pop()

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_position_change_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"][0][
        "position"
    ] = 2

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_path_change_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"][0][
        "path"
    ] = "tampered.json"

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_expected_sha_change_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"][0][
        "expected_sha256"
    ] = "f" * 64

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_actual_sha_change_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"][0][
        "actual_sha256"
    ] = "f" * 64

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_matched_false_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"][0][
        "matched"
    ] = False

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_reason_fails() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["sessions"][0][
        "reason"
    ] = "hash mismatch"

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_verification_global_reasons_fail() -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload["reasons"] = [
        "verification failure"
    ]

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


@pytest.mark.parametrize(
    "field",
    list(CHECKPOINT_SAFETY),
)
def test_verification_safety_change_fails(
    field: str,
) -> None:
    checkpoint = _checkpoint()
    payload = _verification(checkpoint)

    payload[field] = not CHECKPOINT_SAFETY[
        field
    ]

    with pytest.raises(ValueError):
        _validate_verification(
            payload,
            checkpoint,
        )


def test_build_report_without_verification(
    tmp_path: Path,
) -> None:
    protocol_path = _write(
        tmp_path
        / "prospective_microstructure_session11_protocol_20260926.json",
        _protocol(),
    )

    checkpoint_path = _write(
        tmp_path
        / EXPECTED_CHECKPOINT_REFERENCE,
        _checkpoint(),
    )

    report = build_report(
        protocol_path,
        checkpoint_path,
    )

    assert (
        report["status"]
        == "SESSION11_READINESS_OK"
    )

    assert (
        report["ready_for_live_preflight"]
        is True
    )

    assert (
        report["architecture"][
            "checkpoint_verification_validated"
        ]
        is False
    )


def test_build_report_with_verification(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint()

    protocol_path = _write(
        tmp_path
        / "prospective_microstructure_session11_protocol_20260926.json",
        _protocol(),
    )

    checkpoint_path = _write(
        tmp_path
        / EXPECTED_CHECKPOINT_REFERENCE,
        checkpoint,
    )

    verification_path = _write(
        tmp_path
        / "prospective_microstructure_conflict_10session_checkpoint_verify_20260926.json",
        _verification(checkpoint),
    )

    report = build_report(
        protocol_path,
        checkpoint_path,
        verification_path,
    )

    assert (
        report["status"]
        == "SESSION11_READINESS_OK"
    )

    assert (
        report["ready_for_live_preflight"]
        is True
    )

    assert (
        report["checkpoint_verification"][
            "verified"
        ]
        is True
    )

    assert (
        report["checkpoint_verification"][
            "session_count"
        ]
        == 10
    )

    assert (
        report["checkpoint_verification"][
            "identity_count"
        ]
        == 10
    )

    assert (
        report["checkpoint_verification"][
            "all_identities_matched"
        ]
        is True
    )

    assert (
        report["architecture"][
            "checkpoint_verification_validated"
        ]
        is True
    )


def test_build_report_does_not_modify_inputs(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint()

    protocol_path = _write(
        tmp_path
        / "prospective_microstructure_session11_protocol_20260926.json",
        _protocol(),
    )

    checkpoint_path = _write(
        tmp_path
        / EXPECTED_CHECKPOINT_REFERENCE,
        checkpoint,
    )

    verification_path = _write(
        tmp_path
        / "prospective_microstructure_conflict_10session_checkpoint_verify_20260926.json",
        _verification(checkpoint),
    )

    protocol_before = (
        protocol_path.read_bytes()
    )

    checkpoint_before = (
        checkpoint_path.read_bytes()
    )

    verification_before = (
        verification_path.read_bytes()
    )

    build_report(
        protocol_path,
        checkpoint_path,
        verification_path,
    )

    assert (
        protocol_path.read_bytes()
        == protocol_before
    )

    assert (
        checkpoint_path.read_bytes()
        == checkpoint_before
    )

    assert (
        verification_path.read_bytes()
        == verification_before
    )


def test_checkpoint_filename_mismatch_fails(
    tmp_path: Path,
) -> None:
    protocol_path = _write(
        tmp_path
        / "prospective_microstructure_session11_protocol_20260926.json",
        _protocol(),
    )

    checkpoint_path = _write(
        tmp_path / "wrong_checkpoint.json",
        _checkpoint(),
    )

    with pytest.raises(ValueError):
        build_report(
            protocol_path,
            checkpoint_path,
        )


def test_build_report_tampered_verification_fails(
    tmp_path: Path,
) -> None:
    checkpoint = _checkpoint()
    verification = _verification(
        checkpoint
    )

    verification["sessions"][4][
        "actual_sha256"
    ] = "a" * 64

    protocol_path = _write(
        tmp_path
        / "prospective_microstructure_session11_protocol_20260926.json",
        _protocol(),
    )

    checkpoint_path = _write(
        tmp_path
        / EXPECTED_CHECKPOINT_REFERENCE,
        checkpoint,
    )

    verification_path = _write(
        tmp_path / "verification.json",
        verification,
    )

    with pytest.raises(ValueError):
        build_report(
            protocol_path,
            checkpoint_path,
            verification_path,
        )