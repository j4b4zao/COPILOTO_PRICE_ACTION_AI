from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-SESSION11-READINESS"

PROTOCOL_VERSION = (
    "RC1-PROSPECTIVE-MICROSTRUCTURE-INDEPENDENT-SESSION-PROTOCOL"
)

PROTOCOL_NAME = "PROSPECTIVE_MICROSTRUCTURE_SESSION_11"

CHECKPOINT_VERSION = (
    "RC1-PROSPECTIVE-MICROSTRUCTURE-CHECKPOINT-MANIFEST"
)

CHECKPOINT_STATUS = "IDENTITY_LOCK_ONLY"

CHECKPOINT_PROTOCOL = (
    "PROSPECTIVE_MICROSTRUCTURE_CONFLICT_10_SESSION_CHECKPOINT"
)

VERIFICATION_STATUS = "CHECKPOINT_VERIFIED"

EXPECTED_CHECKPOINT_REFERENCE = (
    "prospective_microstructure_conflict_10session_checkpoint_20260926.json"
)

EXPECTED_CHECKPOINT_GIT_COMMIT = "31fe255"

EXPECTED_RUNNER = (
    "tools.profit_rtd_microstructure_prospective_orchestrated_session"
)

EXPECTED_PARAMETERS = {
    "preflight_cycles": 90,
    "preflight_interval": 0.25,
    "cycles": 600,
    "interval": 0.25,
    "max_warmup_cycles": 1800,
    "output_dir": "data/profit_rtd_rc54_3_2",
}

EXPECTED_ADMISSION = {
    "require_trade_context_at_start": True,
    "fail_closed": True,
    "manual_session_substitution_allowed": False,
    "post_result_rule_change_allowed": False,
}

EXPECTED_ANALYSIS = {
    "independent_observation": True,
    "append_to_10session_checkpoint": False,
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

CHECKPOINT_SAFETY = {
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(
            f"required file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return payload


def _require_exact_mapping(
    stage: str,
    actual: Any,
    expected: dict[str, Any],
) -> None:
    if not isinstance(actual, dict):
        raise ValueError(
            f"{stage} must be an object"
        )

    if actual != expected:
        raise ValueError(
            f"{stage} contract changed"
        )


def _validate_protocol(
    payload: dict[str, Any],
) -> None:
    if payload.get("version") != PROTOCOL_VERSION:
        raise ValueError(
            "unexpected session 11 protocol version"
        )

    if payload.get("protocol") != PROTOCOL_NAME:
        raise ValueError(
            "unexpected session 11 protocol name"
        )

    if payload.get("checkpoint_reference") != (
        EXPECTED_CHECKPOINT_REFERENCE
    ):
        raise ValueError(
            "session 11 checkpoint reference changed"
        )

    if payload.get("checkpoint_git_commit") != (
        EXPECTED_CHECKPOINT_GIT_COMMIT
    ):
        raise ValueError(
            "session 11 checkpoint git commit changed"
        )

    if payload.get("session_number") != 11:
        raise ValueError(
            "session number must remain 11"
        )

    if payload.get("symbol") != "WINV26":
        raise ValueError(
            "session 11 symbol changed"
        )

    if payload.get("runner") != EXPECTED_RUNNER:
        raise ValueError(
            "session 11 runner changed"
        )

    _require_exact_mapping(
        "runner_parameters",
        payload.get("runner_parameters"),
        EXPECTED_PARAMETERS,
    )

    _require_exact_mapping(
        "admission_policy",
        payload.get("admission_policy"),
        EXPECTED_ADMISSION,
    )

    _require_exact_mapping(
        "analysis_policy",
        payload.get("analysis_policy"),
        EXPECTED_ANALYSIS,
    )


def _validate_checkpoint(
    payload: dict[str, Any],
) -> None:
    if payload.get("version") != CHECKPOINT_VERSION:
        raise ValueError(
            "unexpected checkpoint version"
        )

    if payload.get("status") != CHECKPOINT_STATUS:
        raise ValueError(
            "checkpoint is not identity locked"
        )

    if payload.get("protocol") != CHECKPOINT_PROTOCOL:
        raise ValueError(
            "unexpected checkpoint protocol"
        )

    if payload.get("session_count") != 10:
        raise ValueError(
            "checkpoint must remain exactly 10 sessions"
        )

    sessions = payload.get("sessions")

    if (
        not isinstance(sessions, list)
        or len(sessions) != 10
    ):
        raise ValueError(
            "checkpoint must contain exactly 10 identities"
        )

    paths: set[str] = set()
    hashes: set[str] = set()

    for expected_position, session in enumerate(
        sessions,
        start=1,
    ):
        if not isinstance(session, dict):
            raise ValueError(
                "invalid checkpoint session identity"
            )

        if session.get("position") != expected_position:
            raise ValueError(
                "checkpoint positions must remain ordered 1..10"
            )

        path = session.get("path")
        digest = session.get("sha256")

        if (
            not isinstance(path, str)
            or not path.strip()
        ):
            raise ValueError(
                "invalid checkpoint session path"
            )

        if (
            not isinstance(digest, str)
            or len(digest) != 64
        ):
            raise ValueError(
                "invalid checkpoint session sha256"
            )

        normalized_hash = digest.lower()

        if path in paths:
            raise ValueError(
                "duplicate checkpoint session path"
            )

        if normalized_hash in hashes:
            raise ValueError(
                "duplicate checkpoint session sha256"
            )

        paths.add(path)
        hashes.add(normalized_hash)

    for key, expected in CHECKPOINT_SAFETY.items():
        if payload.get(key) is not expected:
            raise ValueError(
                f"checkpoint safety contract changed: {key}"
            )


def _validate_verification(
    payload: dict[str, Any],
    checkpoint: dict[str, Any],
) -> None:
    if payload.get("version") != CHECKPOINT_VERSION:
        raise ValueError(
            "unexpected checkpoint verification version"
        )

    if payload.get("status") != VERIFICATION_STATUS:
        raise ValueError(
            "checkpoint verification is not verified"
        )

    if payload.get("verified") is not True:
        raise ValueError(
            "checkpoint verification verified flag is not true"
        )

    if payload.get("protocol") != CHECKPOINT_PROTOCOL:
        raise ValueError(
            "unexpected checkpoint verification protocol"
        )

    if payload.get("session_count") != 10:
        raise ValueError(
            "checkpoint verification must contain exactly 10 sessions"
        )

    sessions = payload.get("sessions")

    if (
        not isinstance(sessions, list)
        or len(sessions) != 10
    ):
        raise ValueError(
            "checkpoint verification must contain exactly 10 identities"
        )

    checkpoint_sessions = checkpoint["sessions"]

    for expected_position, (
        locked,
        verified,
    ) in enumerate(
        zip(checkpoint_sessions, sessions),
        start=1,
    ):
        if not isinstance(verified, dict):
            raise ValueError(
                "invalid checkpoint verification identity"
            )

        if verified.get("position") != expected_position:
            raise ValueError(
                "checkpoint verification positions "
                "must remain ordered 1..10"
            )

        if verified.get("path") != locked["path"]:
            raise ValueError(
                "checkpoint verification path does not "
                "match locked identity"
            )

        expected_sha = verified.get(
            "expected_sha256"
        )

        actual_sha = verified.get(
            "actual_sha256"
        )

        locked_sha = locked["sha256"]

        if expected_sha != locked_sha:
            raise ValueError(
                "checkpoint verification expected sha256 "
                "does not match locked identity"
            )

        if actual_sha != locked_sha:
            raise ValueError(
                "checkpoint verification actual sha256 "
                "does not match locked identity"
            )

        if verified.get("matched") is not True:
            raise ValueError(
                "checkpoint verification identity "
                "is not matched"
            )

        if verified.get("reason") is not None:
            raise ValueError(
                "checkpoint verification identity "
                "has a failure reason"
            )

    reasons = payload.get("reasons")

    if reasons != []:
        raise ValueError(
            "checkpoint verification contains "
            "failure reasons"
        )

    for key, expected in CHECKPOINT_SAFETY.items():
        if payload.get(key) is not expected:
            raise ValueError(
                "checkpoint verification safety "
                f"contract changed: {key}"
            )


def build_report(
    protocol_path: str | Path,
    checkpoint_path: str | Path,
    verification_path: str | Path | None = None,
) -> dict[str, Any]:
    protocol_path = Path(protocol_path)
    checkpoint_path = Path(checkpoint_path)

    verification = None
    verification_file = None
    verification_sha_before = None

    protocol_sha_before = _sha256(
        protocol_path
    )

    checkpoint_sha_before = _sha256(
        checkpoint_path
    )

    protocol = _read_json(
        protocol_path
    )

    checkpoint = _read_json(
        checkpoint_path
    )

    _validate_protocol(protocol)
    _validate_checkpoint(checkpoint)

    if (
        Path(
            protocol["checkpoint_reference"]
        ).name
        != checkpoint_path.name
    ):
        raise ValueError(
            "protocol/checkpoint filename mismatch"
        )

    if verification_path is not None:
        verification_file = Path(
            verification_path
        )

        verification_sha_before = _sha256(
            verification_file
        )

        verification = _read_json(
            verification_file
        )

        _validate_verification(
            verification,
            checkpoint,
        )

    protocol_sha_after = _sha256(
        protocol_path
    )

    checkpoint_sha_after = _sha256(
        checkpoint_path
    )

    if protocol_sha_after != protocol_sha_before:
        raise ValueError(
            "session 11 protocol changed "
            "during readiness check"
        )

    if checkpoint_sha_after != checkpoint_sha_before:
        raise ValueError(
            "checkpoint changed "
            "during readiness check"
        )

    if verification_file is not None:
        verification_sha_after = _sha256(
            verification_file
        )

        if (
            verification_sha_after
            != verification_sha_before
        ):
            raise ValueError(
                "checkpoint verification changed "
                "during readiness check"
            )

    report: dict[str, Any] = {
        "version": VERSION,
        "status": "SESSION11_READINESS_OK",
        "session_number": 11,
        "symbol": "WINV26",
        "protocol": {
            "path": str(protocol_path),
            "sha256": protocol_sha_before,
            "version": protocol["version"],
            "protocol": protocol["protocol"],
        },
        "checkpoint": {
            "path": str(checkpoint_path),
            "sha256": checkpoint_sha_before,
            "version": checkpoint["version"],
            "status": checkpoint["status"],
            "protocol": checkpoint["protocol"],
            "session_count": checkpoint[
                "session_count"
            ],
            "identity_count": len(
                checkpoint["sessions"]
            ),
        },
        "runner": {
            "module": protocol["runner"],
            "parameters": protocol[
                "runner_parameters"
            ],
        },
        "admission_policy": protocol[
            "admission_policy"
        ],
        "analysis_policy": protocol[
            "analysis_policy"
        ],
        "architecture": {
            "protocol_mutated": False,
            "checkpoint_mutated": False,
            "checkpoint_append_allowed": False,
            "manual_session_substitution_allowed": False,
            "post_result_rule_change_allowed": False,
            "automatic_promotion_allowed": False,
        },
        "ready_for_live_preflight": True,
    }

    if verification is not None:
        report["checkpoint_verification"] = {
            "path": str(
                verification_file
            ),
            "sha256": verification_sha_before,
            "version": verification[
                "version"
            ],
            "status": verification[
                "status"
            ],
            "verified": verification[
                "verified"
            ],
            "session_count": verification[
                "session_count"
            ],
            "identity_count": len(
                verification["sessions"]
            ),
            "all_identities_matched": True,
            "failure_reason_count": 0,
        }

        report["architecture"][
            "checkpoint_verification_validated"
        ] = True

    else:
        report["architecture"][
            "checkpoint_verification_validated"
        ] = False

    return report


def _failure_payload(
    error: Exception,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": "SESSION11_READINESS_FAILED",
        "error_type": type(error).__name__,
        "error": str(error),
        "ready_for_live_preflight": False,
        **EXPECTED_ANALYSIS,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed structural readiness "
            "validation for prospective "
            "microstructure session 11. "
            "Does not collect market data and "
            "does not modify the frozen checkpoint."
        )
    )

    parser.add_argument(
        "protocol",
        type=Path,
    )

    parser.add_argument(
        "checkpoint",
        type=Path,
    )

    parser.add_argument(
        "--verification",
        type=Path,
        default=None,
        help=(
            "Optional CHECKPOINT_VERIFIED report. "
            "When supplied, all 10 verified "
            "identities must exactly match the "
            "frozen checkpoint manifest."
        ),
    )

    args = parser.parse_args(argv)

    try:
        report = build_report(
            args.protocol,
            args.checkpoint,
            verification_path=args.verification,
        )

    except Exception as exc:
        print(
            json.dumps(
                _failure_payload(exc),
                ensure_ascii=False,
                indent=2,
            )
        )

        return 1

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())