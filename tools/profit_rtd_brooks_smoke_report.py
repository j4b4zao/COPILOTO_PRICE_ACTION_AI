"""Smoke report final da camada Brooks research-only.

Consolida Registry, Evidence Suite, Integrity Gate, Readiness e Preflight em
um unico relatorio offline. Nao abre Profit/Excel, nao coleta dados reais, nao
executa estrategia e nao promove hipotese.
"""
from __future__ import annotations

import json

from research.price_action.brooks.registry import BrooksResearchRegistry
from tools.profit_rtd_brooks_collection_preflight import run_preflight
from tools.profit_rtd_brooks_integrity_gate import run_integrity_gate
from tools.profit_rtd_brooks_readiness_report import build_readiness_report
from tools.profit_rtd_brooks_research_evidence_suite import AUDITORS, MANAGEMENT_RESEARCH


VERSION = "BROOKS_OFFLINE_SMOKE_REPORT_V1"


def build_smoke_report(*, symbol="WINV26"):
    registry_entries = BrooksResearchRegistry.entries()
    registry_names = [entry.name for entry in registry_entries]
    evidence_names = list(AUDITORS.keys()) + [MANAGEMENT_RESEARCH]

    integrity = run_integrity_gate()
    readiness = build_readiness_report(symbol=symbol)
    preflight = run_preflight(symbol=symbol)

    blockers = []
    if len(registry_entries) != 7:
        blockers.append("REGISTRY_COUNT_INVALID")
    if len(evidence_names) != 7:
        blockers.append("EVIDENCE_FAMILY_COUNT_INVALID")
    if set(registry_names) != set(evidence_names):
        blockers.append("REGISTRY_EVIDENCE_FAMILY_MISMATCH")
    if integrity.get("status") != "PASS":
        blockers.append("INTEGRITY_GATE_FAILED")
    if not readiness.get("offline_infrastructure_ready", False):
        blockers.append("READINESS_NOT_READY")
    if not preflight.get("selection_launcher_allowed", False):
        blockers.append("PREFLIGHT_BLOCKED")

    passed = not blockers
    return {
        "smoke_report": VERSION,
        "symbol": str(symbol),
        "status": "PASS" if passed else "FAIL",
        "offline_stack_ready": passed,
        "registered_family_count": len(registry_entries),
        "evidence_family_count": len(evidence_names),
        "registered_families": registry_names,
        "evidence_families": evidence_names,
        "integrity_gate_status": integrity.get("status"),
        "readiness_status": readiness.get("status"),
        "preflight_status": preflight.get("status"),
        "selection_launcher_allowed": bool(preflight.get("selection_launcher_allowed", False)) if passed else False,
        "selection_only": True,
        "oos_collection_allowed": False,
        "market_data_checked": False,
        "market_open_claimed": False,
        "launcher_executed": False,
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
        "blockers": blockers,
        "next_command": preflight.get("launcher_command") if passed else None,
        "integrity_gate": integrity,
        "readiness": readiness,
        "preflight": preflight,
        "notes": [
            "PASS valida somente coerencia e isolamento da infraestrutura offline Brooks.",
            "Nenhum resultado deste smoke report constitui evidencia preditiva.",
            "A proxima coleta real permanece SELECTION.",
            "O smoke report nunca abre Profit/Excel e nunca executa o launcher.",
        ],
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Smoke report offline final da camada Brooks.")
    parser.add_argument("--symbol", default="WINV26")
    args = parser.parse_args(argv)
    report = build_smoke_report(symbol=args.symbol)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
