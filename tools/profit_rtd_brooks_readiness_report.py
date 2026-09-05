"""Relatorio consolidado de readiness da camada Brooks.

Executa somente verificacoes offline. Nao abre Excel/Profit, nao coleta mercado,
nao classifica sessao como OOS e nao altera Score, Risk, Decision, Alert ou
execucao.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from research.price_action.brooks.registry import BrooksResearchRegistry
from tools.profit_rtd_brooks_integrity_gate import run_integrity_gate


REPORT_VERSION = "BROOKS_COLLECTION_READINESS_REPORT_V1"


def build_readiness_report(*, symbol="WINV26"):
    integrity = run_integrity_gate()
    registry_entries = BrooksResearchRegistry.entries()
    integrity_pass = integrity.get("status") == "PASS"

    blockers = []
    if not integrity_pass:
        blockers.append("INTEGRITY_GATE_FAILED")
    if len(registry_entries) != 7:
        blockers.append("BROOKS_REGISTRY_INCOMPLETE")

    offline_ready = not blockers
    return {
        "report": REPORT_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "symbol": str(symbol),
        "status": "READY_FOR_SELECTION_COLLECTION" if offline_ready else "NOT_READY",
        "offline_infrastructure_ready": offline_ready,
        "market_data_checked": False,
        "market_open_claimed": False,
        "selection_collection_allowed": offline_ready,
        "oos_collection_allowed": False,
        "selection_cutoff_defined": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "registered_family_count": len(registry_entries),
        "registered_families": [entry.name for entry in registry_entries],
        "integrity_gate": integrity,
        "blockers": blockers,
        "next_command": f"python -m tools.profit_rtd_brooks_selection_launcher {symbol}" if offline_ready else None,
        "next_command_mode": "SELECTION" if offline_ready else None,
        "notes": [
            "Readiness significa somente infraestrutura offline pronta.",
            "O launcher deve ser executado apenas quando a fonte real estiver ativa.",
            "As primeiras sessoes novas permanecem SELECTION, nunca OOS automaticamente.",
            "Nenhuma validacao desta camada constitui evidencia de desempenho preditivo.",
        ],
    }


def write_report(report, output_path):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Gera readiness offline da camada Brooks.")
    parser.add_argument("--symbol", default="WINV26")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = build_readiness_report(symbol=args.symbol)
    if args.output:
        write_report(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["offline_infrastructure_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
