"""Orquestrador research-only para coletas Brooks em modo SELECTION.

Executa uma ou mais sessoes pelo runner Brooks enriquecido, coleta os JSONs
produzidos e gera um manifesto de selecao. Nao promove hipoteses, nao executa
OOS e nao altera Score, Risk, Decision, Alert ou ordens.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import tools.profit_rtd_rc54_3_2_brooks_warmed_session as warmed
from tools.profit_rtd_brooks_selection_manifest import build_manifest


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
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "oos_execution_allowed": False,
    }


def run_selection(
    symbol,
    *,
    sessions=1,
    cycles=600,
    interval=0.25,
    max_warmup_cycles=4800,
    output_dir="data/profit_rtd_brooks_selection",
    sleeper=None,
):
    count = int(sessions)
    if count < 1:
        raise ValueError("sessions must be >= 1")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    runs = []
    produced_paths = []

    for index in range(count):
        result = warmed.run_warmed_session(
            symbol,
            cycles=cycles,
            interval=interval,
            max_warmup_cycles=max_warmup_cycles,
            output_dir=str(root),
            sleeper=sleeper,
        )
        output_path = result.get("output_path")
        run = {
            "index": index,
            "status": result.get("status"),
            "data_ready": result.get("data_ready"),
            "analyzable_samples": result.get("analyzable_samples"),
            "collection_errors": result.get("collection_errors"),
            "output_path": str(output_path) if output_path else None,
            "reasons": list(result.get("reasons") or []),
        }
        runs.append(run)
        if output_path:
            produced_paths.append(str(output_path))

    manifest = build_manifest(produced_paths) if produced_paths else {
        "manifest": "BROOKS_SELECTION_SESSION_MANIFEST_V1",
        "mode": "SELECTION",
        "input_sessions": 0,
        "eligible_sessions": 0,
        "rejected_sessions": 0,
        "sessions": [],
        "rejected": [],
        "selection_cutoff": None,
        **_safety(),
    }

    return {
        "runner": "BROOKS_SELECTION_RUNNER_V1",
        "mode": "SELECTION",
        "symbol": symbol,
        "requested_sessions": count,
        "completed_runs": sum(run["status"] == "COMPLETED" for run in runs),
        "produced_session_files": len(produced_paths),
        "runs": runs,
        "manifest": manifest,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Executa coletas Brooks research-only em modo SELECTION.")
    parser.add_argument("symbol")
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--cycles", type=int, default=600)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--max-warmup-cycles", type=int, default=4800)
    parser.add_argument("--output-dir", default="data/profit_rtd_brooks_selection")
    parser.add_argument("--report")
    args = parser.parse_args(argv)

    result = run_selection(
        args.symbol,
        sessions=args.sessions,
        cycles=args.cycles,
        interval=args.interval,
        max_warmup_cycles=args.max_warmup_cycles,
        output_dir=args.output_dir,
    )
    text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False)
    if args.report:
        target = Path(args.report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["produced_session_files"] == result["requested_sessions"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
