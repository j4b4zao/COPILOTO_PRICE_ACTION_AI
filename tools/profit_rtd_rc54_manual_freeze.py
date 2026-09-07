"""Freeze manual e imutavel do conjunto SELECTION RC54.

Este modulo opera apenas sobre evidencias RC54 ja gravadas em disco. Ele exige
revisao pronta, confirmacao humana explicita do cutoff de referencia e grava um
artefato de freeze uma unica vez. Nao abre Excel/Profit, nao coleta mercado, nao
executa estrategia, nao avalia OOS e nao altera Score, Risk, Decision, Alert ou
execucao.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from tools.profit_rtd_rc54_freeze_review_packet import build_packet
from tools.profit_rtd_rc54_inventory_report import DEFAULT_PATTERN


VERSION = "RC54_MANUAL_IMMUTABLE_FREEZE_V1"
CONFIRMATION_TOKEN = "FREEZE_SELECTION"


class FreezeError(ValueError):
    pass


def _sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_core(packet, cutoff):
    accepted_paths = list(packet.get("accepted_selection_paths") or [])
    session_seals = []
    for raw_path in accepted_paths:
        path = Path(raw_path)
        if not path.is_file():
            raise FreezeError(f"ACCEPTED_SESSION_MISSING:{path}")
        session_seals.append({
            "path": str(path),
            "sha256": _sha256_file(path),
        })

    return {
        "freeze_schema": VERSION,
        "selection_cutoff": cutoff,
        "accepted_selection_sessions": len(session_seals),
        "accepted_selection_paths": accepted_paths,
        "session_seals": session_seals,
        "robustness_candidates": list(packet.get("robustness_candidates") or []),
        "selection_interval": packet.get("selection_interval"),
        "source_directory": packet.get("source_directory"),
        "pattern": packet.get("pattern"),
    }


def build_freeze(
    directory,
    *,
    confirmed_cutoff,
    confirmation_token,
    pattern=DEFAULT_PATTERN,
    min_sessions=3,
    min_occurrences_per_session=5,
):
    if confirmation_token != CONFIRMATION_TOKEN:
        raise FreezeError("MANUAL_CONFIRMATION_REQUIRED")

    packet = build_packet(
        directory,
        pattern=pattern,
        min_sessions=min_sessions,
        min_occurrences_per_session=min_occurrences_per_session,
    )
    if packet.get("status") != "READY_FOR_MANUAL_FREEZE_REVIEW":
        raise FreezeError("FREEZE_REVIEW_NOT_READY")
    if not packet.get("manual_freeze_review_allowed"):
        raise FreezeError("MANUAL_FREEZE_REVIEW_NOT_ALLOWED")

    reference_cutoff = packet.get("review_reference_cutoff")
    if not reference_cutoff:
        raise FreezeError("MISSING_REVIEW_REFERENCE_CUTOFF")
    if str(confirmed_cutoff) != str(reference_cutoff):
        raise FreezeError("CONFIRMED_CUTOFF_MISMATCH")

    core = _build_core(packet, str(reference_cutoff))
    freeze_id = hashlib.sha256(_canonical_json(core).encode("utf-8")).hexdigest()
    return {
        **core,
        "freeze_id": freeze_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_cutoff_defined": True,
        "selection_cutoff_is_frozen": True,
        "freeze_immutable": True,
        "manual_confirmation_verified": True,
        "future_oos_collection_allowed": True,
        "oos_collection_started": False,
        "oos_evidence_evaluated": False,
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def write_freeze(output_path, freeze):
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8") as handle:
            json.dump(freeze, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise FreezeError(f"FREEZE_ALREADY_EXISTS:{output}") from exc
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Cria freeze manual e imutavel do SELECTION RC54.")
    parser.add_argument("directory")
    parser.add_argument("--confirm-cutoff", required=True)
    parser.add_argument("--confirm", required=True, help=f"Token obrigatorio: {CONFIRMATION_TOKEN}")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--min-sessions", type=int, default=3)
    parser.add_argument("--min-occurrences-per-session", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    freeze = build_freeze(
        args.directory,
        confirmed_cutoff=args.confirm_cutoff,
        confirmation_token=args.confirm,
        pattern=args.pattern,
        min_sessions=args.min_sessions,
        min_occurrences_per_session=args.min_occurrences_per_session,
    )
    output = write_freeze(args.output, freeze)
    print(f"output_path={output}")
    print(json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
