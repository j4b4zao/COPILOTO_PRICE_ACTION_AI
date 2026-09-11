"""Coleta Brooks de selecao com janela observacional de 30 minutos.

Research-only. Este wrapper reutiliza o runner Brooks warmed ja validado e
altera somente a janela de coleta para permitir sequencias Price Action que
precisam de mais candles M1 para se desenvolver.

Nenhuma informacao produzida aqui altera Score, Risk, Decision, Alert ou
execucao.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.profit_rtd_rc54_3_2_brooks_warmed_session import run_warmed_session


RUNNER = "BROOKS_SELECTION_30MIN_V1"
DEFAULT_CYCLES = 7200
DEFAULT_INTERVAL = 0.25
DEFAULT_DURATION_SECONDS = DEFAULT_CYCLES * DEFAULT_INTERVAL
DEFAULT_OUTPUT_DIR = Path("data/profit_rtd_brooks_selection_30min")


def _safety_flags():
    return {
        "brooks_research_only": True,
        "brooks_predictive_claim_allowed": False,
        "brooks_score_influence_allowed": False,
        "brooks_risk_influence_allowed": False,
        "brooks_decision_influence_allowed": False,
        "brooks_alert_influence_allowed": False,
        "brooks_order_execution_allowed": False,
    }


def run_selection(
    symbol: str,
    *,
    cycles: int = DEFAULT_CYCLES,
    interval: float = DEFAULT_INTERVAL,
    max_warmup_cycles: int = 4800,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    sleeper=None,
):
    if cycles <= 0:
        raise ValueError("cycles must be positive")
    if interval <= 0:
        raise ValueError("interval must be positive")

    result = run_warmed_session(
        symbol,
        cycles=cycles,
        interval=interval,
        max_warmup_cycles=max_warmup_cycles,
        output_dir=str(output_dir),
        sleeper=sleeper,
    )

    result.update(
        {
            "runner": RUNNER,
            "selection_mode": "SELECTION",
            "requested_duration_seconds": cycles * interval,
            "target_exact_candles_m1": 30,
            **_safety_flags(),
        }
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Coleta Brooks research-only com janela padrao de 30 minutos."
    )
    parser.add_argument("symbol")
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--max-warmup-cycles", type=int, default=4800)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args(argv)

    result = run_selection(
        args.symbol,
        cycles=args.cycles,
        interval=args.interval,
        max_warmup_cycles=args.max_warmup_cycles,
        output_dir=args.output_dir,
    )

    print("BROOKS_SELECTION_30MIN=" + str(result.get("status")))
    for key in (
        "runner",
        "symbol",
        "selection_mode",
        "requested_cycles",
        "requested_duration_seconds",
        "target_exact_candles_m1",
        "analyzable_samples",
        "skipped_cycles",
        "collection_errors",
        "data_ready",
        "brooks_breakout_memory_capture",
        "brooks_first_pullback_capture",
        "brooks_major_reversal_context_capture",
        "brooks_wedge_three_pushes_capture",
        "brooks_trading_range_capture",
        "brooks_research_only",
        "brooks_predictive_claim_allowed",
        "brooks_score_influence_allowed",
        "brooks_risk_influence_allowed",
        "brooks_decision_influence_allowed",
        "brooks_alert_influence_allowed",
        "brooks_order_execution_allowed",
    ):
        if key in result:
            print(f"{key}={result[key]}")
    print("reasons=" + ("|".join(result.get("reasons") or []) if result.get("reasons") else "OK"))
    if result.get("output_path"):
        print("output_path=" + str(result["output_path"]))
    return 0 if result.get("status") == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
