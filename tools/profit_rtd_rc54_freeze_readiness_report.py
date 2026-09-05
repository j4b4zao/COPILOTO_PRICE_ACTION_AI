"""Relatorio offline de prontidao para revisao manual de freeze RC54.

Avalia somente sessoes RC54.3.2 ja existentes em disco. Nao cria cutoff, nao
libera OOS, nao abre Excel/Profit, nao coleta mercado e nao altera Score, Risk,
Decision, Alert ou execucao.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_rc54_inventory_report import DEFAULT_PATTERN, discover_sessions
from tools.profit_rtd_rc54_offline_recomposer import recompose


VERSION = "RC54_FREEZE_READINESS_REPORT_V1"


def build_report(
    directory,
    *,
    pattern=DEFAULT_PATTERN,
    min_sessions=3,
    min_occurrences_per_session=5,
):
    paths = discover_sessions(directory, pattern=pattern)
    blockers = []

    if not paths:
        blockers.append("NO_SESSIONS_DISCOVERED")
        return {
            "report": VERSION,
            "status": "NOT_READY",
            "source_directory": str(Path(directory)),
            "pattern": pattern,
            "discovered_sessions": 0,
            "accepted_selection_sessions": 0,
            "quarantined_sessions": 0,
            "robustness_candidates": [],
            "blockers": blockers,
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
    summary = recomposed.get("inventory_summary") or {}
    robustness = recomposed.get("robustness") or {}
    accepted = int(summary.get("accepted_selection_sessions") or 0)
    quarantined = int(summary.get("rejected_sessions") or 0)
    candidates = list(robustness.get("robustness_candidates") or [])

    if accepted < int(min_sessions):
        blockers.append("INSUFFICIENT_INDEPENDENT_SELECTION_SESSIONS")
    if not candidates:
        blockers.append("NO_ROBUSTNESS_CANDIDATE")

    ready = not blockers
    return {
        "report": VERSION,
        "status": "READY_FOR_MANUAL_FREEZE_REVIEW" if ready else "NOT_READY",
        "source_directory": str(Path(directory)),
        "pattern": pattern,
        "discovered_sessions": int(summary.get("discovered_sessions") or len(paths)),
        "accepted_selection_sessions": accepted,
        "quarantined_sessions": quarantined,
        "rejection_reasons": summary.get("rejection_reasons") or {},
        "accepted_selection_paths": list(recomposed.get("accepted_selection_paths") or []),
        "robustness_candidates": candidates,
        "robustness_verdict": robustness.get("verdict"),
        "min_sessions": int(min_sessions),
        "min_occurrences_per_session": int(min_occurrences_per_session),
        "blockers": blockers,
        "manual_freeze_review_allowed": ready,
        "freeze_allowed": False,
        "selection_cutoff_defined": False,
        "selection_cutoff": None,
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
    parser = argparse.ArgumentParser(description="Avalia prontidao offline RC54 para revisao manual de freeze.")
    parser.add_argument("directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--min-sessions", type=int, default=3)
    parser.add_argument("--min-occurrences-per-session", type=int, default=5)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = build_report(
        args.directory,
        pattern=args.pattern,
        min_sessions=args.min_sessions,
        min_occurrences_per_session=args.min_occurrences_per_session,
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"output_path={output}")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
