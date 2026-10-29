"""RC54.3.2 warmed session com enriquecimento Brooks de pesquisa.

Preserva o runner RC54.3.2 original e adiciona somente evidencia
observacional. Nenhuma informacao deste modulo altera PriceActionResult,
Score, Risk, Decision, Alert ou execucao.

Ordem importante:
1. snapshot_context_with_brooks adiciona apenas classificadores que nao
   dependem de candle_evidence;
2. o runner base anexa candle_evidence;
3. apos a sessao, Stop/Target e Trailing sao enriquecidos sobre as amostras
   ja identificadas por candle_id exato.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import tools.profit_rtd_rc54_3_2_warmed_session as base
from tools.profit_rtd_brooks_breakout_memory_capture import (
    enrich_price_action_snapshot as enrich_breakout_memory_snapshot,
)
from tools.profit_rtd_brooks_first_pullback_capture import (
    enrich_price_action_snapshot as enrich_first_pullback_snapshot,
)
from tools.profit_rtd_brooks_wedge_three_pushes_capture import (
    enrich_price_action_snapshot as enrich_wedge_three_pushes_snapshot,
)
from tools.profit_rtd_brooks_trading_range_capture import (
    enrich_price_action_snapshot as enrich_trading_range_snapshot,
)
from tools.profit_rtd_brooks_stop_target_capture import (
    enrich_price_action_snapshot as enrich_stop_target_snapshot,
)
from tools.profit_rtd_brooks_trailing_stop_capture import (
    enrich_price_action_snapshot as enrich_trailing_stop_snapshot,
)


_ORIGINAL_SNAPSHOT_CONTEXT = base.snapshot_context


def _brooks_session_flags():
    return {
        "brooks_breakout_memory_capture": True,
        "brooks_first_pullback_capture": True,
        "brooks_major_reversal_context_capture": True,
        "brooks_wedge_three_pushes_capture": True,
        "brooks_trading_range_capture": True,
        "brooks_stop_target_capture": True,
        "brooks_trailing_stop_capture": True,

        # Contrato EXACT_CANDLE restaurado/consolidado.
        "brooks_stop_target_postprocessed_after_candle_evidence": True,
        "brooks_stop_target_history_source": "PERSISTED_CANDLE_EVIDENCE",
        "brooks_management_postprocessed_after_candle_evidence": True,
        "brooks_management_history_source": "PERSISTED_CANDLE_EVIDENCE",

        "brooks_research_only": True,
        "brooks_predictive_claim_allowed": False,
        "brooks_score_influence_allowed": False,
        "brooks_risk_influence_allowed": False,
        "brooks_decision_influence_allowed": False,
        "brooks_alert_influence_allowed": False,
        "brooks_order_execution_allowed": False,

        "brooks_first_pullback_research_only": True,
        "brooks_first_pullback_predictive_claim_allowed": False,
        "brooks_first_pullback_score_influence_allowed": False,
        "brooks_first_pullback_risk_influence_allowed": False,
        "brooks_first_pullback_decision_influence_allowed": False,
        "brooks_first_pullback_alert_influence_allowed": False,
        "brooks_first_pullback_order_execution_allowed": False,
    }


def snapshot_context_with_brooks(context, micro):
    """Enriquece somente classificadores independentes de candle_evidence."""

    item = _ORIGINAL_SNAPSHOT_CONTEXT(context, micro)
    item = enrich_breakout_memory_snapshot(item, context)
    item = enrich_first_pullback_snapshot(item, context)
    item = enrich_wedge_three_pushes_snapshot(item, context)
    item = enrich_trading_range_snapshot(item, context)

    pa_snapshot = item.get("price_action")
    pa_result = getattr(context, "price_action", None)

    if isinstance(pa_snapshot, dict) and pa_result is not None:
        pa_snapshot["brooks_reversal_context"] = str(
            getattr(pa_result, "brooks_reversal_context", "NEUTRAL")
            or "NEUTRAL"
        )

    return item


def _candle_from_evidence(evidence):
    """Reconstrói candle somente a partir da evidencia persistida."""

    if not isinstance(evidence, dict):
        return None

    if evidence.get("status") != "CANDLE_EVIDENCE_READY":
        return None

    candle_id = evidence.get("candle_id")
    if not candle_id:
        return None

    try:
        return SimpleNamespace(
            candle_id=str(candle_id),
            open=float(evidence["open"]),
            high=float(evidence["high"]),
            low=float(evidence["low"]),
            close=float(evidence["close"]),
            volume=float(evidence.get("volume") or 0.0),
            timestamp=evidence.get("timestamp"),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _management_context(candles):
    """Contexto minimo, somente observacional, para o capture de trailing."""

    return SimpleNamespace(
        market=SimpleNamespace(candles=list(candles))
    )


def _postprocess_stop_target_after_candle_evidence(payload):
    """Aplica apenas Stop/Target sobre candle_evidence persistido.

    Esta funcao e mantida como contrato publico-interno porque testes e
    ferramentas de auditoria podem valida-la isoladamente.
    """

    if not isinstance(payload, dict):
        return payload

    samples = payload.get("samples")
    if not isinstance(samples, list):
        return payload

    for item in samples:
        if not isinstance(item, dict):
            continue

        evidence = item.get("candle_evidence")
        if not isinstance(evidence, dict):
            continue

        if evidence.get("status") != "CANDLE_EVIDENCE_READY":
            continue

        if not evidence.get("candle_id"):
            continue

        # context=None e intencional: impede fallback para market.last_candle.
        enrich_stop_target_snapshot(item, None)

    payload["brooks_stop_target_postprocessed_after_candle_evidence"] = True
    payload["brooks_stop_target_history_source"] = "PERSISTED_CANDLE_EVIDENCE"

    return payload


def _enrich_management_after_candle_evidence(payload):
    """Aplica Stop/Target -> Trailing depois da identidade exata do candle.

    Revisoes do mesmo candle atualizam o ultimo candle em vez de adicionar
    um novo elemento. Quando o candle_id muda, o anterior passa a fazer parte
    do historico fechado e o novo candle ocupa a ultima posicao.

    Esta funcao tambem e usada pelo management reprocessor offline.
    """

    if not isinstance(payload, dict):
        return payload

    samples = payload.get("samples")
    if not isinstance(samples, list):
        return payload

    candles = []
    last_candle_id = None

    for item in samples:
        if not isinstance(item, dict):
            continue

        evidence = item.get("candle_evidence")
        candle = _candle_from_evidence(evidence)

        if candle is not None:
            if candle.candle_id == last_candle_id and candles:
                # EXACT_CANDLE_LAST_REVISION para o candle corrente.
                candles[-1] = candle
            else:
                candles.append(candle)
                last_candle_id = candle.candle_id

        # Stop/Target depende exclusivamente do candle_evidence ja persistido.
        if (
            isinstance(evidence, dict)
            and evidence.get("status") == "CANDLE_EVIDENCE_READY"
            and evidence.get("candle_id")
        ):
            enrich_stop_target_snapshot(item, None)

        # Trailing usa somente o historico reconstruido da evidencia persistida.
        enrich_trailing_stop_snapshot(
            item,
            _management_context(candles),
        )

    payload["brooks_stop_target_postprocessed_after_candle_evidence"] = True
    payload["brooks_stop_target_history_source"] = "PERSISTED_CANDLE_EVIDENCE"

    payload["brooks_management_postprocessed_after_candle_evidence"] = True
    payload["brooks_management_history_source"] = "PERSISTED_CANDLE_EVIDENCE"

    return payload


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

    flags = _brooks_session_flags()
    result.update(flags)

    output_path = result.get("output_path")

    if output_path:
        path = Path(output_path)
        payload = json.loads(path.read_text(encoding="utf-8"))

        payload = _enrich_management_after_candle_evidence(payload)
        payload.update(flags)

        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="RC54.3.2 warmed session com evidencia observacional Brooks."
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
        "brooks_breakout_memory_capture",
        "brooks_first_pullback_capture",
        "brooks_major_reversal_context_capture",
        "brooks_wedge_three_pushes_capture",
        "brooks_trading_range_capture",
        "brooks_stop_target_capture",
        "brooks_trailing_stop_capture",
        "brooks_stop_target_postprocessed_after_candle_evidence",
        "brooks_stop_target_history_source",
        "brooks_management_postprocessed_after_candle_evidence",
        "brooks_management_history_source",
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
        + (
            "|".join(result.get("reasons") or [])
            if result.get("reasons")
            else "OK"
        )
    )

    if result.get("output_path"):
        print("output_path=" + str(result["output_path"]))

    return 0 if result.get("status") == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
