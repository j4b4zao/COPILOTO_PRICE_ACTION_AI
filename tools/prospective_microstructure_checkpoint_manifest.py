"""Manifest imutável de checkpoints prospectivos de microestrutura.

Este utilitário congela somente a identidade de uma coorte já definida:

- ordem das sessões;
- path informado;
- SHA-256 exato de cada arquivo;
- quantidade de sessões;
- protocolo/label informado pelo pesquisador.

Ele NÃO:
- descobre sessões por glob;
- redefine coortes;
- calcula métricas de mercado;
- avalia performance;
- produz sinal;
- influencia Score/Risk/Decision/Alert;
- autoriza execução ou promoção.

Uso:

Criar:
    python -m tools.prospective_microstructure_checkpoint_manifest create \
        --protocol PROSPECTIVE_MICROSTRUCTURE_CONFLICT_10_SESSION_CHECKPOINT \
        --output checkpoint.json \
        session1.json session2.json

Verificar:
    python -m tools.prospective_microstructure_checkpoint_manifest verify \
        checkpoint.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-CHECKPOINT-MANIFEST"
STATUS = "IDENTITY_LOCK_ONLY"

_FALSE_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
)


def _safety() -> dict:
    return {
        "research_only": True,
        "observational_only": True,
        **{name: False for name in _FALSE_FLAGS},
    }


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise ValueError(
            f"unable to read session: {path}: {type(exc).__name__}"
        ) from exc


def _validate_unique_sessions(sessions: list[dict]) -> None:
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()

    for index, session in enumerate(sessions, start=1):
        path = session["path"]
        digest = session["sha256"]

        normalized = str(Path(path).resolve()).casefold()

        if normalized in seen_paths:
            raise ValueError(
                f"duplicate session path at position {index}: {path}"
            )

        if digest in seen_hashes:
            raise ValueError(
                f"duplicate session sha256 at position {index}: {digest}"
            )

        seen_paths.add(normalized)
        seen_hashes.add(digest)


def create_manifest(
    paths,
    *,
    protocol: str,
) -> dict:
    paths = list(paths)

    if not paths:
        raise ValueError("at least one session path is required")

    if not isinstance(protocol, str) or not protocol.strip():
        raise ValueError("protocol must be a non-empty string")

    sessions: list[dict] = []

    for position, raw_path in enumerate(paths, start=1):
        path = Path(raw_path)

        raw = _read_bytes(path)
        digest = _sha256(raw)

        sessions.append(
            {
                "position": position,
                "path": str(path),
                "sha256": digest,
            }
        )

    _validate_unique_sessions(sessions)

    return {
        "version": VERSION,
        "status": STATUS,
        "protocol": protocol.strip(),
        "session_count": len(sessions),
        "sessions": sessions,
        **_safety(),
    }


def _validate_manifest_structure(payload: dict) -> list[str]:
    reasons: list[str] = []

    if not isinstance(payload, dict):
        return ["MANIFEST_NOT_OBJECT"]

    if payload.get("version") != VERSION:
        reasons.append("UNEXPECTED_MANIFEST_VERSION")

    if payload.get("status") != STATUS:
        reasons.append("UNEXPECTED_MANIFEST_STATUS")

    protocol = payload.get("protocol")
    if not isinstance(protocol, str) or not protocol.strip():
        reasons.append("INVALID_PROTOCOL")

    session_count = payload.get("session_count")
    if (
        isinstance(session_count, bool)
        or not isinstance(session_count, int)
        or session_count <= 0
    ):
        reasons.append("INVALID_SESSION_COUNT")

    sessions = payload.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        reasons.append("INVALID_SESSIONS")
        return reasons

    if isinstance(session_count, int) and not isinstance(
        session_count, bool
    ):
        if session_count != len(sessions):
            reasons.append("SESSION_COUNT_MISMATCH")

    expected_positions = list(range(1, len(sessions) + 1))
    actual_positions: list[int] = []

    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()

    for index, session in enumerate(sessions, start=1):
        if not isinstance(session, dict):
            reasons.append(f"SESSION_{index}_NOT_OBJECT")
            continue

        position = session.get("position")
        path = session.get("path")
        digest = session.get("sha256")

        if isinstance(position, bool) or not isinstance(position, int):
            reasons.append(f"SESSION_{index}_INVALID_POSITION")
        else:
            actual_positions.append(position)

        if not isinstance(path, str) or not path:
            reasons.append(f"SESSION_{index}_INVALID_PATH")
        else:
            normalized = str(Path(path).resolve()).casefold()
            if normalized in seen_paths:
                reasons.append(f"SESSION_{index}_DUPLICATE_PATH")
            seen_paths.add(normalized)

        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in digest.lower()
            )
        ):
            reasons.append(f"SESSION_{index}_INVALID_SHA256")
        else:
            lowered = digest.lower()
            if lowered in seen_hashes:
                reasons.append(f"SESSION_{index}_DUPLICATE_SHA256")
            seen_hashes.add(lowered)

    if actual_positions != expected_positions:
        reasons.append("SESSION_ORDER_INVALID")

    safety = _safety()

    for key, expected in safety.items():
        if payload.get(key) is not expected:
            reasons.append(f"SAFETY_FLAG_INVALID:{key}")

    return reasons


def verify_manifest(payload: dict) -> dict:
    structural_reasons = _validate_manifest_structure(payload)

    if structural_reasons:
        return {
            "version": VERSION,
            "status": "MANIFEST_INVALID",
            "verified": False,
            "reasons": structural_reasons,
            **_safety(),
        }

    results: list[dict] = []
    reasons: list[str] = []

    sessions = payload["sessions"]

    for session in sessions:
        position = session["position"]
        raw_path = session["path"]
        expected_sha256 = session["sha256"].lower()

        path = Path(raw_path)

        try:
            actual_sha256 = _sha256(path.read_bytes())
        except OSError as exc:
            actual_sha256 = None
            matched = False
            reason = f"UNREADABLE:{type(exc).__name__}"
        else:
            matched = actual_sha256 == expected_sha256
            reason = None if matched else "SHA256_MISMATCH"

        if not matched:
            reasons.append(
                f"SESSION_{position}:{reason}"
            )

        results.append(
            {
                "position": position,
                "path": raw_path,
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "matched": matched,
                "reason": reason,
            }
        )

    verified = not reasons

    return {
        "version": VERSION,
        "status": (
            "CHECKPOINT_VERIFIED"
            if verified
            else "CHECKPOINT_MISMATCH"
        ),
        "verified": verified,
        "protocol": payload["protocol"],
        "session_count": payload["session_count"],
        "sessions": results,
        "reasons": reasons,
        **_safety(),
    }


def _load_manifest(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8-sig")
        payload = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"unable to load manifest: {path}: {type(exc).__name__}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("manifest top-level JSON must be an object")

    return payload


def _write_json(path: Path, payload: dict) -> None:
    rendered = json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    )
    path.write_text(rendered + "\n", encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    create_parser = subparsers.add_parser(
        "create",
        help="create an identity-only checkpoint manifest",
    )
    create_parser.add_argument(
        "paths",
        nargs="+",
        help="explicit session paths in frozen order",
    )
    create_parser.add_argument(
        "--protocol",
        required=True,
        help="protocol/checkpoint identifier",
    )
    create_parser.add_argument(
        "--output",
        required=True,
        help="output JSON manifest path",
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="verify files against an existing manifest",
    )
    verify_parser.add_argument(
        "manifest",
        help="manifest JSON path",
    )
    verify_parser.add_argument(
        "--output",
        help="optional verification report JSON path",
    )

    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "create":
            result = create_manifest(
                args.paths,
                protocol=args.protocol,
            )

            _write_json(
                Path(args.output),
                result,
            )

        elif args.command == "verify":
            manifest = _load_manifest(
                Path(args.manifest)
            )

            result = verify_manifest(manifest)

            if args.output:
                _write_json(
                    Path(args.output),
                    result,
                )

        else:
            parser.error("unsupported command")
            return 2

    except ValueError as exc:
        print(
            json.dumps(
                {
                    "version": VERSION,
                    "status": "ERROR",
                    "error": str(exc),
                    **_safety(),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    if args.command == "verify":
        return 0 if result["verified"] else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())