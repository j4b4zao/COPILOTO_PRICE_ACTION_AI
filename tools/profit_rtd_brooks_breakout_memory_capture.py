"""Memoria observacional de breakout para pesquisa Brooks.

Esta camada existe somente para pesquisa. Ela NAO altera PriceActionResult,
Score, Risk, Decision, Alert ou execucao.

Motivacao
---------
BreakoutDynamics descreve apenas o breakout imediatamente anterior. Para uma
auditoria de breakout-pullback precisamos conservar o nivel rompido por mais
candles, sem modificar o produtor operacional.

A memoria e reconstruida deterministicamente a partir dos candles fechados;
nao depende de estado global entre ciclos.
"""

from __future__ import annotations


MAX_TRACK_BARS = 20
MIN_BASE_CANDLES = 3


def _closed(candles):
    return list(candles[:-1]) if candles else []


def _find_latest_breakout(closed, *, max_track_bars=MAX_TRACK_BARS):
    if len(closed) < MIN_BASE_CANDLES + 1:
        return None

    start = max(MIN_BASE_CANDLES, len(closed) - int(max_track_bars) - 1)
    latest = None

    for index in range(start, len(closed)):
        base = closed[:index]
        if len(base) < MIN_BASE_CANDLES:
            continue

        bar = closed[index]
        range_high = max(float(c.high) for c in base)
        range_low = min(float(c.low) for c in base)
        close = float(bar.close)

        if close > range_high:
            latest = {
                "index": index,
                "direction": "UP",
                "level": float(range_high),
                "breakout_close": close,
            }
        elif close < range_low:
            latest = {
                "index": index,
                "direction": "DOWN",
                "level": float(range_low),
                "breakout_close": close,
            }

    if latest is None:
        return None

    age = len(closed) - 1 - latest["index"]
    if age > int(max_track_bars):
        return None

    return latest


def snapshot_breakout_memory(context, *, max_track_bars=MAX_TRACK_BARS):
    market = getattr(context, "market", None)
    candles_obj = getattr(market, "candles", None)
    candles = candles_obj.all() if candles_obj is not None and hasattr(candles_obj, "all") else []
    closed = _closed(candles)

    state = _find_latest_breakout(closed, max_track_bars=max_track_bars)
    phase = "NO_ACTIVE_BREAKOUT"
    direction = "NONE"
    level = 0.0
    age_bars = 0
    tested = False
    held = False
    failed = False
    resumed = False

    if state is not None:
        direction = state["direction"]
        level = state["level"]
        age_bars = len(closed) - 1 - state["index"]
        phase = "BREAKOUT_ACTIVE"

        for bar in closed[state["index"] + 1:]:
            high = float(bar.high)
            low = float(bar.low)
            close = float(bar.close)
            open_ = float(bar.open)

            if direction == "UP":
                if close < level:
                    failed = True
                    phase = "BREAKOUT_FAILED"
                    break
                if low <= level and close >= level:
                    tested = True
                    held = True
                    phase = "BREAKOUT_TESTED"
                    continue
                if tested and close > state["breakout_close"] and close > open_:
                    resumed = True
                    phase = "BREAKOUT_RESUMED"
            else:
                if close > level:
                    failed = True
                    phase = "BREAKOUT_FAILED"
                    break
                if high >= level and close <= level:
                    tested = True
                    held = True
                    phase = "BREAKOUT_TESTED"
                    continue
                if tested and close < state["breakout_close"] and close < open_:
                    resumed = True
                    phase = "BREAKOUT_RESUMED"

    return {
        "brooks_research_breakout_memory_phase": phase,
        "brooks_research_breakout_memory_direction": direction,
        "brooks_research_breakout_memory_level": float(level),
        "brooks_research_breakout_memory_age_bars": int(age_bars),
        "brooks_research_breakout_memory_tested": bool(tested),
        "brooks_research_breakout_memory_held": bool(held),
        "brooks_research_breakout_memory_failed": bool(failed),
        "brooks_research_breakout_memory_resumed": bool(resumed),
        "brooks_research_breakout_memory_max_track_bars": int(max_track_bars),
        "brooks_research_only": True,
        "brooks_predictive_claim_allowed": False,
        "brooks_score_influence_allowed": False,
        "brooks_risk_influence_allowed": False,
        "brooks_decision_influence_allowed": False,
        "brooks_alert_influence_allowed": False,
        "brooks_order_execution_allowed": False,
    }


def enrich_price_action_snapshot(item, context):
    if not isinstance(item, dict):
        raise TypeError("item must be dict")
    price_action = item.setdefault("price_action", {})
    if not isinstance(price_action, dict):
        raise TypeError("item['price_action'] must be dict")
    price_action.update(snapshot_breakout_memory(context))
    return item
