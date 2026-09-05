"""Captura observacional de FirstPullbackSequenceDynamics para sessoes EXACT_CANDLE.

Esta camada existe somente para pesquisa Brooks. Ela nao altera PriceActionResult,
Score, Risk, Decision, Alert ou execucao.
"""

from __future__ import annotations

from analysis.price_action.first_pullback_sequence_dynamics import (
    FirstPullbackSequenceDynamics,
)


def snapshot_first_pullback(context):
    """Executa o detector diagnostico em candles fechados e devolve campos estaveis."""
    market = getattr(context, "market", None)
    candles_obj = getattr(market, "candles", None)
    candles = candles_obj.all() if candles_obj is not None and hasattr(candles_obj, "all") else []

    result = FirstPullbackSequenceDynamics().analyze(candles)

    return {
        "brooks_first_pullback_valid": bool(result.valid),
        "brooks_first_pullback_direction": str(result.direction or "NONE"),
        "brooks_first_pullback_stage": str(result.stage or "NO_SEQUENCE"),
        "brooks_first_pullback_stage_index": int(result.stage_index or 0),
        "brooks_first_pullback_bars": int(result.first_pullback_bars or 0),
        "brooks_first_pullback_minor_trendline_break": bool(result.minor_trendline_break),
        "brooks_first_pullback_moving_average_touch": bool(result.moving_average_touch),
        "brooks_first_pullback_moving_average_close_cross": bool(result.moving_average_close_cross),
        "brooks_first_pullback_moving_average_gap_bar": bool(result.moving_average_gap_bar),
        "brooks_first_pullback_major_trendline_break": bool(result.major_trendline_break),
        "brooks_first_pullback_long_two_leg_pullback": bool(result.long_two_leg_pullback),
        "brooks_first_pullback_two_sided_trading": bool(result.two_sided_trading),
        "brooks_first_pullback_trading_range_transition": bool(result.trading_range_transition),
        "brooks_first_pullback_trend_maturity_score": float(result.trend_maturity_score or 0.0),
        "brooks_first_pullback_continuation_bias": bool(result.continuation_bias),
        "brooks_first_pullback_reversal_risk": bool(result.reversal_risk),
        "brooks_first_pullback_reasons": list(result.reasons),
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def enrich_price_action_snapshot(item, context):
    """Anexa a evidencia de pesquisa ao bloco price_action de uma amostra RC54."""
    if not isinstance(item, dict):
        raise TypeError("item must be dict")
    price_action = item.setdefault("price_action", {})
    if not isinstance(price_action, dict):
        raise TypeError("item['price_action'] must be dict")
    price_action.update(snapshot_first_pullback(context))
    return item
