"""
tools/profit_rtd_brooks_trailing_stop_capture.py

Captura observacional de gerenciamento Brooks - trailing stop estrutural.

Este modulo e research-only. Ele:
- reutiliza a geometria inicial de stop ja capturada pelo Brooks Stop/Target;
- usa somente o historico de candles do MarketState;
- calcula um proposed_stop diagnostico;
- nao altera RiskManager, Score, Decision, Alert ou execucao;
- nao move stop real;
- nao cria parcial;
- nao calcula outcome.

Nesta primeira etapa, current_stop e igual ao initial_stop. A persistencia de um
stop hipotetico entre candles sera tratada somente em uma etapa posterior e
com auditoria dedicada.
"""

from __future__ import annotations

from analysis.price_action.protective_trailing_stop_dynamics import (
    ProtectiveTrailingStopDynamics,
)


_ENGINE = ProtectiveTrailingStopDynamics()


def _safety_fields():
    return {
        "brooks_management_research_only": True,
        "brooks_management_observational_only": True,
        "brooks_management_predictive_claim_allowed": False,
        "brooks_management_score_influence_allowed": False,
        "brooks_management_risk_influence_allowed": False,
        "brooks_management_decision_influence_allowed": False,
        "brooks_management_alert_influence_allowed": False,
        "brooks_management_order_execution_allowed": False,
    }


def enrich_price_action_snapshot(item, context=None):
    if not isinstance(item, dict):
        raise TypeError("item must be dict")

    pa = item.setdefault("price_action", {})
    if not isinstance(pa, dict):
        raise TypeError("item['price_action'] must be dict")

    direction = str(
        pa.get("brooks_stop_target_direction")
        or pa.get("brooks_signal_direction")
        or "NONE"
    ).strip().upper()

    if direction == "UP":
        direction = "BUY"
    elif direction == "DOWN":
        direction = "SELL"

    entry_triggered = bool(
        pa.get("brooks_stop_target_entry_triggered")
        or pa.get("brooks_entry_triggered")
    )

    entry_price = float(
        pa.get("brooks_stop_target_entry_price") or 0.0
    )
    initial_stop = float(
        pa.get("brooks_stop_target_initial_stop") or 0.0
    )
    stop_geometry_valid = bool(
        pa.get("brooks_stop_target_stop_geometry_valid")
    )

    market = getattr(context, "market", None) if context is not None else None
    candle_history = getattr(market, "candles", None) if market is not None else None
    candles = list(candle_history) if candle_history is not None else []

    eligible = (
        entry_triggered
        and stop_geometry_valid
        and direction in {"BUY", "SELL"}
        and entry_price > 0.0
        and initial_stop > 0.0
        and len(candles) >= ProtectiveTrailingStopDynamics.MIN_HISTORY + 1
    )

    pa.update(_safety_fields())
    pa["brooks_management_component"] = "TRAILING_STOP_V1"
    pa["brooks_management_capture_status"] = (
        "ELIGIBLE" if eligible else "NOT_ELIGIBLE"
    )
    pa["brooks_management_direction"] = direction
    pa["brooks_management_entry_triggered"] = entry_triggered
    pa["brooks_management_entry_price"] = entry_price
    pa["brooks_management_initial_stop"] = initial_stop
    pa["brooks_management_current_stop"] = initial_stop
    pa["brooks_management_proposed_stop"] = initial_stop
    pa["brooks_management_state"] = "NO_STOP_CONTEXT"
    pa["brooks_management_trailing_active"] = False
    pa["brooks_management_stop_improved"] = False
    pa["brooks_management_stop_loosened"] = False
    pa["brooks_management_structural_advance_confirmed"] = False
    pa["brooks_management_latest_swing_index"] = -1
    pa["brooks_management_latest_swing_price"] = 0.0
    pa["brooks_management_protected_r"] = 0.0
    pa["brooks_management_reason"] = "NOT_ELIGIBLE"
    pa["brooks_management_reasons"] = ["NOT_ELIGIBLE"]

    if not eligible:
        reasons = []
        if not entry_triggered:
            reasons.append("ENTRY_NOT_TRIGGERED")
        if direction not in {"BUY", "SELL"}:
            reasons.append("INVALID_DIRECTION")
        if not stop_geometry_valid:
            reasons.append("INITIAL_STOP_GEOMETRY_NOT_VALIDATED")
        if entry_price <= 0.0:
            reasons.append("INVALID_ENTRY_PRICE")
        if initial_stop <= 0.0:
            reasons.append("INVALID_INITIAL_STOP")
        if len(candles) < ProtectiveTrailingStopDynamics.MIN_HISTORY + 1:
            reasons.append("INSUFFICIENT_HISTORY")

        pa["brooks_management_reason"] = (
            reasons[-1] if reasons else "NOT_ELIGIBLE"
        )
        pa["brooks_management_reasons"] = reasons or ["NOT_ELIGIBLE"]
        return item

    result = _ENGINE.analyze(
        candles,
        direction=direction,
        entry_price=entry_price,
        initial_stop=initial_stop,
        current_stop=initial_stop,
        tick_size=1.0,
    )

    pa.update({
        "brooks_management_capture_status": (
            "CAPTURED" if result.valid else "REJECTED"
        ),
        "brooks_management_direction": result.direction,
        "brooks_management_entry_price": result.entry_price,
        "brooks_management_initial_stop": result.initial_stop,
        "brooks_management_current_stop": result.current_stop,
        "brooks_management_proposed_stop": result.proposed_stop,
        "brooks_management_state": result.state,
        "brooks_management_trailing_active": result.trailing_active,
        "brooks_management_stop_improved": result.stop_improved,
        "brooks_management_stop_loosened": result.stop_loosened,
        "brooks_management_structural_advance_confirmed": (
            result.structural_advance_confirmed
        ),
        "brooks_management_latest_swing_index": result.latest_swing_index,
        "brooks_management_latest_swing_price": result.latest_swing_price,
        "brooks_management_protected_r": result.protected_r,
        "brooks_management_reason": result.reason,
        "brooks_management_reasons": list(result.reasons),
    })

    return item
