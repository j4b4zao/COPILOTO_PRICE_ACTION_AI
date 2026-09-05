"""Pre-flight fail-closed para coleta Brooks em modo SELECTION.

Executa Integrity Gate + Readiness Report antes de liberar o launcher. Nao
verifica horario de mercado, nao abre Excel/Profit e nao inicia coleta por conta
propria. O resultado apenas autoriza ou bloqueia a proxima acao manual.
"""
from __future__ import annotations

import json

from tools.profit_rtd_brooks_integrity_gate import run_integrity_gate
from tools.profit_rtd_brooks_readiness_report import build_readiness_report


VERSION = "BROOKS_COLLECTION_PREFLIGHT_V1"


def run_preflight(*, symbol="WINV26"):
    integrity = run_integrity_gate()
    readiness = build_readiness_report(symbol=symbol)

    blockers = []
    if integrity.get("status") != "PASS":
        blockers.append("INTEGRITY_GATE_FAILED")
    if not readiness.get("offline_infrastructure_ready", False):
        blockers.append("READINESS_NOT_READY")
    if readiness.get("oos_collection_allowed") is not False:
        blockers.append("OOS_GUARD_INVALID")
    if readiness.get("next_command_mode") != "SELECTION":
        blockers.append("SELECTION_MODE_NOT_ENFORCED")

    allowed = not blockers
    command = f"python -m tools.profit_rtd_brooks_selection_launcher {symbol}" if allowed else None

    return {
        "preflight": VERSION,
        "symbol": str(symbol),
        "status": "PASS" if allowed else "BLOCKED",
        "selection_launcher_allowed": allowed,
        "launcher_command": command,
        "launcher_mode": "SELECTION" if allowed else None,
        "market_data_checked": False,
        "market_open_claimed": False,
        "launcher_executed": False,
        "oos_collection_allowed": False,
        "selection_cutoff_defined": False,
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
        "integrity_gate_status": integrity.get("status"),
        "readiness_status": readiness.get("status"),
        "readiness": readiness,
        "notes": [
            "PASS libera somente o proximo comando manual de coleta SELECTION.",
            "O pre-flight nao confirma que o mercado ou a fonte RTD estejam ativos.",
            "O pre-flight nunca inicia o launcher automaticamente.",
            "OOS permanece bloqueado ate existir cutoff formal e evidencia futura independente.",
        ],
    }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Pre-flight offline da coleta Brooks SELECTION.")
    parser.add_argument("--symbol", default="WINV26")
    args = parser.parse_args(argv)
    report = run_preflight(symbol=args.symbol)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["selection_launcher_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
