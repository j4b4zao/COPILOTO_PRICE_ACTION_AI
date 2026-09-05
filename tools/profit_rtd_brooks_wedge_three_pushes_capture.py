"""Captura research-only para BROOKS_WEDGE_THREE_PUSHES_V1."""
from __future__ import annotations

from research.price_action.brooks.wedge_three_pushes import BrooksThreePushesDetector


def enrich_price_action_snapshot(item, context):
    pa = item.setdefault("price_action", {})
    candles = list(getattr(getattr(context, "market", None), "history", []) or [])
    detection = BrooksThreePushesDetector.analyze(candles)
    pa["brooks_three_pushes_detected"] = bool(detection.detected)
    pa["brooks_three_pushes_direction"] = str(detection.push_direction)
    pa["brooks_three_pushes_indices"] = list(detection.push_indices)
    pa["brooks_three_pushes_prices"] = list(detection.push_prices)
    pa["brooks_three_pushes_narrowing"] = bool(detection.narrowing)
    return item
