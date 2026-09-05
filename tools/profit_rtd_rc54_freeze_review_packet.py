"""Pacote offline para revisao manual de freeze RC54.

Consolida inventario, prontidao e metadados das sessoes SELECTION elegiveis ja
existentes em disco. Nao cria nem grava cutoff, nao libera OOS, nao abre
Excel/Profit, nao coleta mercado e nao altera Score, Risk, Decision, Alert ou
execucao.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tools.profit_rtd_rc54_freeze_readiness_report import build_report as build_readiness_report
from tools.profit_rtd_rc54_inventory_report import DEFAULT_PATTERN, discover_sessions
from tools.profit_rtd_rc54_offline_recomposer import recompose


VERSION = "RC54_FREEZE_REVIEW_PACKET_V1"


def _timestamp(value):
    return datetime.fromisoformat(str(value))


def build_packet(
    directory,
    *,
    pattern=DEFAULT_PATTERN,
    min_sessions=3,
    min_occurrences_per_session=5,
):
    readiness = build_readiness_report(
        directory,
        pattern=pattern,
        min_sessions=min_sessions,
        min_occurrences_per_session=min_occurrences_per_session,
    )
    paths = discover_sessions(directory, pattern=pattern)

    if not paths:
        return {
            "packet": VERSION,
            "status": "NOT_READY",
            "source_directory": str(Path(directory)),
            "pattern": pattern,
            "readiness": readiness,
            "accepted_selection_sessions": 0,
            "accepted_selection_paths": [],
            "quarantined_sessions": [],
            "robustness_candidates": [],
            "candidate_details": {},
            "selection_interval": None,
            "review_reference_cutoff": None,
            "review_reference_cutoff_is_frozen": False,
            "manual_freeze_review_allowed": False,
            "freeze_allowed": False,
            "selection_cutoff_defined": False,
            "oos_allowed": False,
            "research_only": True,
            "observational_only": True,
            "predictive_claim_allowed": False,
            "score_influence_allowed": False,
            "risk_influence_allowed": False,
            "decision_influence_allowed": False,
            "alert_influence_allowed": False,
            "order_execution_allowed": False,
        }

    recomposed = recompose(
        paths,
        min_sessions=min_sessions,
        min_occurrences_per_session=min_occurrences_per_session,
        inventory_mode=True,
    )
    manifest = list(recomposed.get("manifest") or [])
    accepted_rows = [
        row for row in manifest
        if row.get("role") == "SELECTION" and row.get("eligible")
    ]
    quarantined = [row for row in manifest if not row.get("eligible")]
    robustness = recomposed.get("robustness") or {}
    candidates = list(robustness.get("robustness_candidates") or [])
    buckets = robustness.get("buckets") or {}

    first_timestamp = None
    last_timestamp = None
    if accepted_rows:
        first_timestamp = min(_timestamp(row["first_timestamp"]) for row in accepted_rows).isoformat()
        last_timestamp = max(_timestamp(row["last_timestamp"]) for row in accepted_rows).isoformat()

    candidate_details = {
        candidate: {
            "supported_sessions": buckets.get(candidate, {}).get("supported_sessions"),
            "consistent_horizons": buckets.get(candidate, {}).get("consistent_horizons"),
            "evidence_gap": buckets.get(candidate, {}).get("evidence_gap"),
            "robustness_candidate": buckets.get(candidate, {}).get("robustness_candidate", False),
        }
        for candidate in candidates
    }

    ready = bool(readiness.get("manual_freeze_review_allowed"))
    return {
        "packet": VERSION,
        "status": "READY_FOR_MANUAL_FREEZE_REVIEW" if ready else "NOT_READY",
        "source_directory": str(Path(directory)),
        "pattern": pattern,
        "readiness": readiness,
        "accepted_selection_sessions": len(accepted_rows),
        "accepted_selection_paths": [row["path"] for row in accepted_rows],
        "quarantined_sessions": quarantined,
        "robustness_candidates": candidates,
        "candidate_details": candidate_details,
        "selection_interval": (
            {"first_timestamp": first_timestamp, "last_timestamp": last_timestamp}
            if accepted_rows else None
        ),
        "review_reference_cutoff": last_timestamp if ready else None,
        "review_reference_cutoff_is_frozen": False,
        "manual_freeze_review_allowed": ready,
        "freeze_allowed": False,
        "selection_cutoff_defined": False,
        "oos_allowed": False,
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera pacote offline RC54 para revisao manual de freeze.")
    parser.add_argument("directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--min-sessions", type=int, default=3)
    parser.add_argument("--min-occurrences-per-session", type=int, default=5)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    packet = build_packet(
        args.directory,
        pattern=args.pattern,
        min_sessions=args.min_sessions,
        min_occurrences_per_session=args.min_occurrences_per_session,
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"output_path={output}")
    print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
