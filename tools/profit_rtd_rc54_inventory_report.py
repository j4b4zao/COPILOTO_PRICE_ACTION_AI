"""Relatorio offline de inventario limpo para evidencias RC54.

Descobre apenas arquivos RC54.3.2 ja existentes em disco e delega toda a
validacao ao recompositor offline RC54. Nao abre Excel/Profit, nao coleta mercado,
nao executa estrategia e nao altera Score, Risk, Decision, Alert ou execucao.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_rc54_offline_recomposer import recompose


VERSION = "RC54_CLEAN_INVENTORY_REPORT_V1"
DEFAULT_PATTERN = "profit_rtd_rc54_3_2_*.json"


def discover_sessions(directory, pattern=DEFAULT_PATTERN):
    root = Path(directory)
    if not root.exists():
        return []
    return sorted(path for path in root.glob(pattern) if path.is_file())


def build_report(directory, *, pattern=DEFAULT_PATTERN):
    paths = discover_sessions(directory, pattern=pattern)
    if not paths:
        return {
            "report": VERSION,
            "status": "NO_SESSIONS_DISCOVERED",
            "source_directory": str(Path(directory)),
            "pattern": pattern,
            "discovered_sessions": 0,
            "accepted_selection_sessions": 0,
            "rejected_sessions": 0,
            "rejection_reasons": {},
            "accepted_selection_paths": [],
            "quarantined_sessions": [],
            "freeze_allowed": False,
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

    recomposed = recompose(paths, inventory_mode=True)
    summary = recomposed.get("inventory_summary") or {}
    manifest = recomposed.get("manifest") or []
    quarantined = [row for row in manifest if not row.get("eligible")]

    accepted_count = int(summary.get("accepted_selection_sessions") or 0)
    rejected_count = int(summary.get("rejected_sessions") or 0)
    status = "CLEAN" if rejected_count == 0 else "CLEAN_WITH_QUARANTINE"

    return {
        "report": VERSION,
        "status": status,
        "source_directory": str(Path(directory)),
        "pattern": pattern,
        "discovered_sessions": int(summary.get("discovered_sessions") or len(paths)),
        "accepted_selection_sessions": accepted_count,
        "rejected_sessions": rejected_count,
        "rejection_reasons": summary.get("rejection_reasons") or {},
        "accepted_selection_paths": list(recomposed.get("accepted_selection_paths") or []),
        "quarantined_sessions": quarantined,
        "recomposer_verdict": recomposed.get("verdict"),
        "manifest_valid": bool(recomposed.get("manifest_valid")),
        "freeze_allowed": False,
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
    parser = argparse.ArgumentParser(description="Gera relatorio offline de inventario limpo RC54.")
    parser.add_argument("directory")
    parser.add_argument("--pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = build_report(args.directory, pattern=args.pattern)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"output_path={output}")

    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
