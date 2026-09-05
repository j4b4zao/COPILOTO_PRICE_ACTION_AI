"""Ledger offline de tentativas Brooks em modo SELECTION.

Varre relatorios JSON ja produzidos pelo Selection Launcher, classifica cada
execucao com BROOKS_SELECTION_OUTCOME_V1 e consolida um inventario seguro.
Nao abre Excel/Profit, nao coleta mercado, nao executa estrategia e nao libera
OOS automaticamente.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_brooks_selection_outcome import classify_report

VERSION = "BROOKS_SELECTION_LEDGER_V1"
DEFAULT_REPORT_DIR = "data/profit_rtd_brooks_selection_reports"


def _safety():
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
        "hypothesis_freeze_allowed": False,
        "oos_collection_allowed": False,
    }


def inspect_report(path):
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "path": str(source),
            "status": "REJECTED",
            "counts_as_selection_evidence": False,
            "reason": "REPORT_UNREADABLE",
            "error": type(exc).__name__,
        }

    try:
        outcome = classify_report(payload)
    except (TypeError, ValueError, OverflowError) as exc:
        return {
            "path": str(source),
            "status": "REJECTED",
            "counts_as_selection_evidence": False,
            "reason": "OUTCOME_CLASSIFICATION_FAILED",
            "error": type(exc).__name__,
        }

    return {
        "path": str(source),
        "symbol": payload.get("symbol"),
        "launcher": payload.get("launcher"),
        "status": outcome["status"],
        "counts_as_selection_evidence": outcome["counts_as_selection_evidence"],
        "retry_when_real_source_active": outcome["retry_when_real_source_active"],
        "requested_sessions": outcome["requested_sessions"],
        "produced_session_files": outcome["produced_session_files"],
        "eligible_sessions": outcome["eligible_sessions"],
        "rejected_sessions": outcome["rejected_sessions"],
        "selection_cutoff": outcome["selection_cutoff"],
        "reasons": outcome["reasons"],
    }


def build_ledger(paths):
    entries = [inspect_report(path) for path in paths]
    entries.sort(key=lambda item: item["path"])

    counts = {
        "VALID_SELECTION": 0,
        "NO_VALID_SOURCE": 0,
        "REJECTED": 0,
        "INCOMPLETE": 0,
    }
    for item in entries:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    valid = [item for item in entries if item["status"] == "VALID_SELECTION"]
    attempts_without_source = [item for item in entries if item["status"] == "NO_VALID_SOURCE"]
    rejected = [item for item in entries if item["status"] == "REJECTED"]
    incomplete = [item for item in entries if item["status"] == "INCOMPLETE"]

    selection_evidence_sessions = sum(int(item.get("eligible_sessions") or 0) for item in valid)
    cutoffs = [item.get("selection_cutoff") for item in valid if item.get("selection_cutoff")]

    return {
        "ledger": VERSION,
        "report_count": len(entries),
        "status_counts": counts,
        "valid_selection_reports": len(valid),
        "no_valid_source_reports": len(attempts_without_source),
        "rejected_reports": len(rejected),
        "incomplete_reports": len(incomplete),
        "selection_evidence_sessions": selection_evidence_sessions,
        "latest_observed_selection_cutoff": max(cutoffs) if cutoffs else None,
        "selection_cutoff_defined_for_oos": False,
        "entries": entries,
        "valid_selection": valid,
        "no_valid_source": attempts_without_source,
        "rejected": rejected,
        "incomplete": incomplete,
        **_safety(),
    }


def discover_reports(report_dir=DEFAULT_REPORT_DIR):
    root = Path(report_dir)
    if not root.exists():
        return []
    return sorted(root.glob("brooks_selection_*.json"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Consolida relatorios Brooks SELECTION ja existentes.")
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)

    paths = [Path(path) for path in args.paths] if args.paths else discover_reports(args.report_dir)
    result = build_ledger(paths)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["rejected_reports"] == 0 and result["incomplete_reports"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
