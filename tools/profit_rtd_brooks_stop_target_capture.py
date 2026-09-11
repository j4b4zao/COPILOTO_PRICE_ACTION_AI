"""Captura observacional de geometria Brooks de stop e alvo estrutural.

Registra somente uma hipotese descritiva no snapshot de pesquisa. Nao cria,
move ou envia stops/alvos e nao acessa RiskManager, DecisionEngine ou execucao.
"""
from __future__ import annotations


def _direction(value):
    value = str(value or "NONE").strip().upper()
    if value in {"UP", "BUY", "BULL", "BULLISH"}:
        return "BUY"
    if value in {"DOWN", "SELL", "BEAR", "BEARISH"}:
        return "SELL"
    return "NONE"


def enrich_price_action_snapshot(item, context=None):
    if not isinstance(item, dict):
        raise TypeError("item must be dict")
    pa = item.setdefault("price_action", {})
    if not isinstance(pa, dict):
        raise TypeError("item['price_action'] must be dict")

    candle = item.get("candle_evidence") or {}
    direction = _direction(pa.get("brooks_signal_direction"))
    triggered = bool(pa.get("brooks_entry_triggered"))
    ready = candle.get("status") == "CANDLE_EVIDENCE_READY" and bool(candle.get("ohlc_ready", True))

    entry = float(candle.get("close") or 0.0) if ready else 0.0
    low = float(candle.get("low") or 0.0) if ready else 0.0
    high = float(candle.get("high") or 0.0) if ready else 0.0
    stop = low if direction == "BUY" else high if direction == "SELL" else 0.0
    stop_valid = (
        triggered and entry > 0 and
        ((direction == "BUY" and 0 < stop < entry) or (direction == "SELL" and stop > entry))
    )

    range_valid = bool(pa.get("brooks_trading_range_valid"))
    target = 0.0
    target_source = "NONE"
    if range_valid and direction == "BUY":
        target = float(pa.get("brooks_trading_range_high") or 0.0)
        target_source = "TRADING_RANGE_OPPOSITE_EDGE"
    elif range_valid and direction == "SELL":
        target = float(pa.get("brooks_trading_range_low") or 0.0)
        target_source = "TRADING_RANGE_OPPOSITE_EDGE"
    target_valid = (
        triggered and stop_valid and
        ((direction == "BUY" and target > entry) or (direction == "SELL" and 0 < target < entry))
    )
    risk = abs(entry - stop) if stop_valid else 0.0
    reward = abs(target - entry) if target_valid else 0.0

    reasons = []
    if not triggered:
        reasons.append("ENTRY_NOT_TRIGGERED")
    if direction == "NONE":
        reasons.append("INVALID_DIRECTION")
    if triggered and not stop_valid:
        reasons.append("SIGNAL_CANDLE_STOP_GEOMETRY_INVALID")
    if stop_valid:
        reasons.append("SIGNAL_CANDLE_STOP_GEOMETRY_VALID")
    if not range_valid:
        reasons.append("STRUCTURAL_TARGET_NOT_AVAILABLE")
    elif not target_valid:
        reasons.append("STRUCTURAL_TARGET_GEOMETRY_INVALID")
    else:
        reasons.append("STRUCTURAL_TARGET_GEOMETRY_VALID")

    pa.update({
        "brooks_stop_target_capture_status": "ELIGIBLE" if stop_valid else "NOT_ELIGIBLE",
        "brooks_stop_target_direction": direction,
        "brooks_stop_target_entry_triggered": triggered,
        "brooks_stop_target_entry_price": entry,
        "brooks_stop_target_initial_stop": stop,
        "brooks_stop_target_stop_geometry_valid": stop_valid,
        "brooks_stop_target_target_price": target if target_valid else 0.0,
        "brooks_stop_target_target_valid": target_valid,
        "brooks_stop_target_target_source": target_source if target_valid else "NONE",
        "brooks_stop_target_reward_risk": (reward / risk) if risk > 0 and target_valid else 0.0,
        "brooks_stop_target_candle_id": candle.get("candle_id"),
        "brooks_stop_target_reasons": reasons,
        "brooks_stop_target_research_only": True,
        "brooks_stop_target_observational_only": True,
        "brooks_stop_target_predictive_claim_allowed": False,
        "brooks_stop_target_score_influence_allowed": False,
        "brooks_stop_target_risk_influence_allowed": False,
        "brooks_stop_target_decision_influence_allowed": False,
        "brooks_stop_target_alert_influence_allowed": False,
        "brooks_stop_target_order_execution_allowed": False,
    })
    return item
