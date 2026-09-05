"""Launcher operacional de um comando para coletas Brooks em SELECTION.

Foi desenhado para uso manual em mercado aberto. Encapsula o Selection Runner,
define caminhos de saida previsiveis, classifica o outcome da tentativa e grava
um relatorio JSON da execucao.

Nao executa OOS e nao permite qualquer influencia operacional.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from tools.profit_rtd_brooks_selection_outcome import classify_report
from tools.profit_rtd_brooks_selection_runner import run_selection

DEFAULT_OUTPUT_DIR = "data/profit_rtd_brooks_selection"
DEFAULT_REPORT_DIR = "data/profit_rtd_brooks_selection_reports"


def _stamp(now=None):
    current = now or datetime.now()
    return current.strftime("%Y%m%d_%H%M%S")


def build_report_path(symbol, *, report_dir=DEFAULT_REPORT_DIR, now=None):
    safe_symbol = "".join(ch for ch in str(symbol).upper() if ch.isalnum() or ch in {"-", "_"}) or "UNKNOWN"
    return Path(report_dir) / f"brooks_selection_{safe_symbol}_{_stamp(now)}.json"


def launch_selection(
    symbol,
    *,
    sessions=1,
    cycles=600,
    interval=0.25,
    max_warmup_cycles=4800,
    output_dir=DEFAULT_OUTPUT_DIR,
    report_dir=DEFAULT_REPORT_DIR,
    sleeper=None,
    now=None,
):
    result = run_selection(
        symbol,
        sessions=sessions,
        cycles=cycles,
        interval=interval,
        max_warmup_cycles=max_warmup_cycles,
        output_dir=output_dir,
        sleeper=sleeper,
    )

    report_path = build_report_path(symbol, report_dir=report_dir, now=now)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    base_report = {
        **result,
        "launcher": "BROOKS_SELECTION_LAUNCHER_V1",
        "report_path": str(report_path),
    }
    selection_outcome = classify_report(base_report)
    result = {
        **base_report,
        "selection_outcome": selection_outcome,
    }

    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Launcher de um comando para coleta Brooks research-only em modo SELECTION."
    )
    parser.add_argument("symbol")
    parser.add_argument("--sessions", type=int, default=1)
    parser.add_argument("--cycles", type=int, default=600)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--max-warmup-cycles", type=int, default=4800)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    args = parser.parse_args(argv)

    result = launch_selection(
        args.symbol,
        sessions=args.sessions,
        cycles=args.cycles,
        interval=args.interval,
        max_warmup_cycles=args.max_warmup_cycles,
        output_dir=args.output_dir,
        report_dir=args.report_dir,
    )

    manifest = result.get("manifest") or {}
    outcome = result.get("selection_outcome") or {}
    print("BROOKS_SELECTION_LAUNCHER=" + str(result.get("launcher")))
    print("mode=" + str(result.get("mode")))
    print("symbol=" + str(result.get("symbol")))
    print("requested_sessions=" + str(result.get("requested_sessions")))
    print("produced_session_files=" + str(result.get("produced_session_files")))
    print("eligible_sessions=" + str(manifest.get("eligible_sessions")))
    print("rejected_sessions=" + str(manifest.get("rejected_sessions")))
    print("selection_cutoff=" + str(manifest.get("selection_cutoff")))
    print("selection_outcome=" + str(outcome.get("status")))
    print("counts_as_selection_evidence=" + str(outcome.get("counts_as_selection_evidence")))
    print("retry_when_real_source_active=" + str(outcome.get("retry_when_real_source_active")))
    print("report_path=" + str(result.get("report_path")))

    status = outcome.get("status")
    return 0 if status in {"VALID_SELECTION", "NO_VALID_SOURCE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
