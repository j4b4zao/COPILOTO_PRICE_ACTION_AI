from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-INDEPENDENT-SESSION-COMPARISON"

CHECKPOINT_VERSION = (
    "RC1-PROSPECTIVE-MICROSTRUCTURE-CHECKPOINT-MANIFEST"
)

CHECKPOINT_STATUS = "IDENTITY_LOCK_ONLY"

CHECKPOINT_PROTOCOL = (
    "PROSPECTIVE_MICROSTRUCTURE_CONFLICT_10_SESSION_CHECKPOINT"
)

_FALSE_SAFETY_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
)

_PIPELINE_STAGES = (
    "coverage",
    "episodes",
    "followthrough",
    "stratification",
    "stability",
)


def _safety() -> dict[str, bool]:
    return {
        "research_only": True,
        "observational_only": True,
        **{
            key: False
            for key in _FALSE_SAFETY_FLAGS
        },
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
            f"not a readable file: {path}"
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


def _validate_safety(
    stage: str,
    payload: dict[str, Any],
) -> None:
    expected = _safety()

    for key, expected_value in expected.items():
        if payload.get(key) is not expected_value:
            raise ValueError(
                f"{stage}: unsafe or missing flag "
                f"{key}={payload.get(key)!r}; "
                f"expected {expected_value!r}"
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
            "baseline must be an identity-locked checkpoint"
        )

    if payload.get("protocol") != CHECKPOINT_PROTOCOL:
        raise ValueError(
            "unexpected checkpoint protocol"
        )

    if payload.get("session_count") != 10:
        raise ValueError(
            "baseline must remain the frozen "
            "10-session checkpoint"
        )

    sessions = payload.get("sessions")

    if (
        not isinstance(sessions, list)
        or len(sessions) != 10
    ):
        raise ValueError(
            "baseline must contain exactly "
            "10 locked session identities"
        )

    positions: set[int] = set()
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

        position = session.get("position")
        path = session.get("path")
        sha256 = session.get("sha256")

        if position != expected_position:
            raise ValueError(
                "checkpoint session positions "
                "must be ordered 1..10"
            )

        if (
            not isinstance(path, str)
            or not path.strip()
        ):
            raise ValueError(
                "checkpoint session path is invalid"
            )

        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
        ):
            raise ValueError(
                "checkpoint session sha256 is invalid"
            )

        normalized_sha = sha256.lower()

        if position in positions:
            raise ValueError(
                "duplicate checkpoint session position"
            )

        if path in paths:
            raise ValueError(
                "duplicate checkpoint session path"
            )

        if normalized_sha in hashes:
            raise ValueError(
                "duplicate checkpoint session sha256"
            )

        positions.add(position)
        paths.add(path)
        hashes.add(normalized_sha)

    _validate_safety(
        "checkpoint",
        payload,
    )


def _validate_independent_audit(
    payload: dict[str, Any],
) -> None:
    if (
        payload.get("status")
        != "POST_SESSION_AUDIT_COMPLETED"
    ):
        raise ValueError(
            "independent audit is not completed"
        )

    if payload.get("session_count") != 1:
        raise ValueError(
            "audit must contain a single independent session"
        )

    input_sessions = payload.get("input_sessions")

    if (
        not isinstance(input_sessions, list)
        or len(input_sessions) != 1
    ):
        raise ValueError(
            "audit must identify exactly one "
            "independent session"
        )

    independent = input_sessions[0]

    if not isinstance(independent, dict):
        raise ValueError(
            "invalid independent session identity"
        )

    sha256 = independent.get("sha256")

    if (
        not isinstance(sha256, str)
        or len(sha256) != 64
    ):
        raise ValueError(
            "independent session sha256 is invalid"
        )

    pipeline = payload.get("pipeline")

    if not isinstance(pipeline, dict):
        raise ValueError(
            "incomplete independent audit pipeline"
        )

    for stage in _PIPELINE_STAGES:
        if pipeline.get(stage) != "COMPLETED":
            raise ValueError(
                "incomplete independent audit pipeline: "
                f"{stage}"
            )

    _validate_safety(
        "independent audit",
        payload,
    )


def _validate_independence(
    checkpoint: dict[str, Any],
    audit: dict[str, Any],
) -> None:
    baseline_hashes = {
        str(session["sha256"]).lower()
        for session in checkpoint["sessions"]
    }

    independent_sha = str(
        audit["input_sessions"][0]["sha256"]
    ).lower()

    if independent_sha in baseline_hashes:
        raise ValueError(
            "independent session already belongs "
            "to frozen baseline"
        )


def build_report(
    checkpoint_path: str | Path,
    independent_audit_path: str | Path,
) -> dict[str, Any]:
    checkpoint_path = Path(checkpoint_path)
    independent_audit_path = Path(
        independent_audit_path
    )

    checkpoint_sha_before = _sha256(
        checkpoint_path
    )
    audit_sha_before = _sha256(
        independent_audit_path
    )

    checkpoint = _read_json(
        checkpoint_path
    )
    audit = _read_json(
        independent_audit_path
    )

    _validate_checkpoint(checkpoint)
    _validate_independent_audit(audit)
    _validate_independence(
        checkpoint,
        audit,
    )

    independent_session = (
        audit["input_sessions"][0]
    )

    report: dict[str, Any] = {
        "version": VERSION,
        "status": (
            "INDEPENDENT_SESSION_COMPARISON_COMPLETED"
        ),
        "baseline": {
            "path": str(checkpoint_path),
            "sha256": checkpoint_sha_before,
            "version": checkpoint["version"],
            "session_count": 10,
            "protocol": checkpoint["protocol"],
            "status": checkpoint["status"],
            "identity_count": len(
                checkpoint["sessions"]
            ),
        },
        "independent": {
            "audit_path": str(
                independent_audit_path
            ),
            "sha256": audit_sha_before,
            "session_count": 1,
            "session": independent_session,
            "audit_version": audit.get(
                "version"
            ),
            "audit_status": audit.get(
                "status"
            ),
        },
        "comparison": {
            "mode": (
                "FROZEN_BASELINE_VS_"
                "INDEPENDENT_OBSERVATION"
            ),
            "baseline_session_count": 10,
            "independent_session_count": 1,
            "combined_session_count": None,
            "combined_checkpoint_created": False,
            "interpretation": "DESCRIPTIVE_ONLY",
        },
        "architecture": {
            "baseline_mutated": False,
            "independent_appended_to_baseline": False,
            "baseline_overlap_allowed": False,
            "automatic_promotion_allowed": False,
            "glob_discovery_allowed": False,
        },
        **_safety(),
    }

    checkpoint_sha_after = _sha256(
        checkpoint_path
    )
    audit_sha_after = _sha256(
        independent_audit_path
    )

    if (
        checkpoint_sha_after
        != checkpoint_sha_before
    ):
        raise ValueError(
            "checkpoint changed during comparison"
        )

    if audit_sha_after != audit_sha_before:
        raise ValueError(
            "independent audit changed during comparison"
        )

    return report


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the frozen identity-locked "
            "prospective microstructure 10-session "
            "checkpoint with one independent "
            "post-session audit. Research-only and "
            "descriptive-only. The independent "
            "observation is never appended to the "
            "baseline."
        )
    )

    parser.add_argument(
        "checkpoint",
        type=Path,
        help=(
            "Frozen identity-locked 10-session "
            "checkpoint manifest."
        ),
    )

    parser.add_argument(
        "independent_audit",
        type=Path,
        help=(
            "Completed single-session "
            "Post-Session Audit RC1 JSON."
        ),
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output comparison JSON.",
    )

    args = parser.parse_args()

    try:
        report = build_report(
            args.checkpoint,
            args.independent_audit,
        )

        _write_json(
            args.output,
            report,
        )

    except Exception as exc:
        failure = {
            "version": VERSION,
            "status": (
                "INDEPENDENT_SESSION_COMPARISON_FAILED"
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
            **_safety(),
        }

        print(
            json.dumps(
                failure,
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