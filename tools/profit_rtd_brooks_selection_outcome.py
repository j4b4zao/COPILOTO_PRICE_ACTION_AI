"""Classificador offline do resultado de uma tentativa Brooks SELECTION.

Interpreta apenas o relatorio JSON ja gravado pelo Selection Launcher. Nao abre
Excel/Profit, nao coleta mercado e nao altera Score, Risk, Decision, Alert ou
execucao.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


VERSION = "BROOKS_SELECTION_OUTCOME_V1"


def classify_report(report):
    if not isinstance(report, dict):
        raise TypeError("report must be a dict")

    mode = str(report.get("mode") or "").upper()
    produced = int(report.get("produced_session_files") or 0)
    requested = int(report.get("requested_sessions") or 0)
    manifest = report.get("manifest") or {}
    eligible = int(manifest.get("eligible_sessions") or 0)
    rejected = int(manifest.get("rejected_sessions") or 0)
    selection_cutoff = manifest.get("selection_cutoff")

    reasons = []

    if mode != "SELECTION":
        status = "REJECTED"
        reasons.append("MODE_NOT_SELECTION")
    elif produced == 0 and eligible == 0 and rejected == 0:
        status = "NO_VALID_SOURCE"
        reasons.append("NO_SESSION_PRODUCED")
    elif rejected > 0:
        status = "REJECTED"
        reasons.append("MANIFEST_REJECTIONS_PRESENT")
    elif requested > 0 and produced != requested:
        status = "INCOMPLETE"
        reasons.append("REQUESTED_SESSION_COUNT_NOT_MET")
    elif produced > 0 and eligible == produced and rejected == 0:
        status = "VALID_SELECTION"
        reasons.append("SELECTION_SESSION_ACCEPTED")
    else:
        status = "INCOMPLETE"
        reasons.append("SELECTION_RESULT_INCOMPLETE")

    return {
        "outcome": VERSION,
        "status": status,
        "mode": mode or None,
        "requested_sessions": requested,
        "produced_session_files": produced,
        "eligible_sessions": eligible,
        "rejected_sessions": rejected,
        "selection_cutoff": selection_cutoff,
        "counts_as_selection_evidence": status == "VALID_SELECTION",
        "counts_as_oos_evidence": False,
        "retry_when_real_source_active": status == "NO_VALID_SOURCE",
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
        "reasons": reasons,
    }


def classify_path(path):
    source = Path(path)
    report = json.loads(source.read_text(encoding="utf-8"))
    result = classify_report(report)
    return {**result, "source_report": str(source)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Classifica relatorio Brooks SELECTION ja existente.")
    parser.add_argument("report_path")
    args = parser.parse_args(argv)
    result = classify_path(args.report_path)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"VALID_SELECTION", "NO_VALID_SOURCE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
