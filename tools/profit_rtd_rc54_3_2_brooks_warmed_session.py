"""RC54.3.2 warmed session com enriquecimento Brooks de pesquisa.

Este runner preserva o RC54.3.2 original e adiciona somente evidencia
observacional ao bloco ``price_action`` de cada amostra. Nenhuma informacao
deste modulo altera PriceActionResult, Score, Risk, Decision, Alert ou
execucao.

A implementacao e deliberadamente derivada: o runner validado
``profit_rtd_rc54_3_2_warmed_session`` continua intacto. Aqui apenas
substituimos, durante esta execucao, a funcao de snapshot usada por ele por
uma versao enriquecida para pesquisa Brooks.
"""

from __future__ import annotations

import argparse
import json

import tools.profit_rtd_rc54_3_2_warmed_session as base
from tools.profit_rtd_brooks_first_pullback_capture import (
    enrich_price_action_snapshot,
)


_ORIGINAL_SNAPSHOT_CONTEXT = base.snapshot_context


def snapshot_context_with_brooks(context, micro):
    """Snapshot RC54.3 enriquecido apenas com evidencia Brooks de pesquisa."""
    item = _ORIGINAL_SNAPSHOT_CONTEXT(context, micro)
    item = enrich_price_action_snapshot(item, context)

    pa_snapshot = item.get("price_action")
    pa_result = getattr(context, "price_action", None)
    if isinstance(pa_snapshot, dict) and pa_result is not None:
        pa_snapshot["brooks_reversal_context"] = str(
            getattr(pa_result, "brooks_reversal_context", "NEUTRAL") or "NEUTRAL"
        )

    return item


def run_warmed_session(
    symbol,
    *,
    cycles=600,
    interval=0.25,
    max_warmup_cycles=4800,
    require_trade_context_at_start=False,
    output_dir=None,
    sleeper=None,
):
    """Executa RC54.3.2 com captura Brooks sem modificar o runner original."""
    previous = base.snapshot_context
    base.snapshot_context = snapshot_context_with_brooks
    try:
        kwargs = {
            "cycles": cycles,
            "interval": interval,
            "max_warmup_cycles": max_warmup_cycles,
            "require_trade_context_at_start": require_trade_context_at_start,
            "output_dir": output_dir,
        }
        if sleeper is not None:
            kwargs["sleeper"] = sleeper
        result = base.run_warmed_session(symbol, **kwargs)
    finally:
        base.snapshot_context = previous

    result["brooks_first_pullback_capture"] = True
    result["brooks_major_reversal_context_capture"] = True
    result["brooks_research_only"] = True
    result["brooks_predictive_claim_allowed"] = False
    result["brooks_score_influence_allowed"] = False
    result["brooks_risk_influence_allowed"] = False
    result["brooks_decision_influence_allowed"] = False
    result["brooks_alert_influence_allowed"] = False
    result["brooks_order_execution_allowed"] = False

    result["brooks_first_pullback_research_only"] = True
    result["brooks_first_pullback_predictive_claim_allowed"] = False
    result["brooks_first_pullback_score_influence_allowed"] = False
    result["brooks_first_pullback_risk_influence_allowed"] = False
    result["brooks_first_pullback_decision_influence_allowed"] = False
    result["brooks_first_pullback_alert_influence_allowed"] = False
    result["brooks_first_pullback_order_execution_allowed"] = False
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "RC54.3.2 warmed session com evidencia observacional Brooks."
        )
    )
    parser.add_argument("symbol")
    parser.add_argument("--cycles", type=int, default=600)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--max-warmup-cycles", type=int, default=4800)
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)

    result = run_warmed_session(
        args.symbol,
        cycles=args.cycles,
        interval=args.interval,
        max_warmup_cycles=args.max_warmup_cycles,
        output_dir=args.output_dir,
    )

    print(
        "PROFIT_RTD_RC54_3_2_BROOKS_WARMED_SESSION="
        + str(result.get("status"))
    )
    for key in (
        "symbol",
        "requested_cycles",
        "analyzable_samples",
        "skipped_cycles",
        "collection_errors",
        "data_ready",
        "brooks_first_pullback_capture",
        "brooks_major_reversal_context_capture",
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
    if result.get("collection_error_details"):
        print(
            "collection_error_details="
            + json.dumps(
                result["collection_error_details"],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    print(
        "reasons="
        + ("|".join(result.get("reasons") or []) if result.get("reasons") else "OK")
    )
    if result.get("output_path"):
        print("output_path=" + str(result["output_path"]))
    return 0 if result.get("status") == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
