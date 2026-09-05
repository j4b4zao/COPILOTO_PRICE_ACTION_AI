"""Captura research-only para BROOKS_TRADING_RANGE_REVERSAL_V1."""
from __future__ import annotations

from analysis.price_action.trading_range_playbook_dynamics import TradingRangePlaybookDynamics


def enrich_price_action_snapshot(item, context):
    pa = item.setdefault("price_action", {})
    candles = list(getattr(getattr(context, "market", None), "history", []) or [])
    result = TradingRangePlaybookDynamics().analyze(candles)

    pa["brooks_trading_range_valid"] = bool(result.valid)
    pa["brooks_trading_range_state"] = str(result.state)
    pa["brooks_trading_range_low"] = float(result.range_low)
    pa["brooks_trading_range_high"] = float(result.range_high)
    pa["brooks_trading_range_mid"] = float(result.range_mid)
    pa["brooks_trading_range_height"] = float(result.range_height)
    pa["brooks_trading_range_position"] = float(result.position)
    pa["brooks_trading_range_zone"] = str(result.zone)
    pa["brooks_trading_range_setup_direction"] = str(result.setup_direction)
    pa["brooks_trading_range_h2_near_low"] = bool(result.h2_near_low)
    pa["brooks_trading_range_l2_near_high"] = bool(result.l2_near_high)
    pa["brooks_trading_range_breakout_attempt"] = bool(result.breakout_attempt)
    pa["brooks_trading_range_failed_breakout_risk"] = bool(result.failed_breakout_risk)
    pa["brooks_trading_range_avoid_middle"] = bool(result.avoid_middle)
    pa["brooks_trading_range_reasons"] = list(result.reasons)
    return item
