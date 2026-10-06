"""External market observational view RC2.

Descriptive interpretation only. It consumes RC1 monitor output and exposes
per-asset observed direction plus data-quality coverage. It does not infer a
trading regime, BUY/SELL direction, score, risk, decision, alert, or order.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any


class ExternalMarketObservationalView:
    VERSION = "RC2"
    ASSETS = ("US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD")
    USABLE_STATUS = "AVAILABLE"

    @staticmethod
    def _observed_direction(status: str, change: Any) -> str:
        if status != "AVAILABLE":
            return "UNAVAILABLE"
        if isinstance(change, bool):
            return "UNAVAILABLE"
        try:
            value = float(change)
        except (TypeError, ValueError, OverflowError):
            return "UNAVAILABLE"
        if not isfinite(value):
            return "UNAVAILABLE"
        if value > 0:
            return "POSITIVE"
        if value < 0:
            return "NEGATIVE"
        return "FLAT"

    @classmethod
    def build(cls, monitor: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(monitor, dict):
            raise TypeError("monitor must be a dict")
        source = deepcopy(monitor)
        if source.get("observational_only") is not True:
            raise ValueError("RC2 accepts observational monitor data only")
        if source.get("operational_influence_allowed") is not False:
            raise ValueError("operational influence must remain disabled")
        if source.get("automatic_activation") is not False:
            raise ValueError("automatic activation must remain disabled")
        rows = source.get("assets")
        readiness = source.get("readiness")
        if not isinstance(rows, list) or not isinstance(readiness, dict):
            raise ValueError("invalid RC1 monitor contract")

        by_asset = {}
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("monitor asset rows must be dicts")
            asset = row.get("asset")
            if asset not in cls.ASSETS or asset in by_asset:
                raise ValueError("unsupported or duplicate asset")
            status = row.get("status")
            by_asset[asset] = {
                "asset": asset,
                "status": status,
                "observed_direction": cls._observed_direction(status, row.get("change")),
                "price": row.get("price"),
                "change": row.get("change"),
                "timestamp": row.get("timestamp"),
                "provider": row.get("provider"),
                "provider_symbol": row.get("provider_symbol"),
                "reasons": list(row.get("reasons") or ()),
            }

        missing_rows = [asset for asset in cls.ASSETS if asset not in by_asset]
        if missing_rows:
            raise ValueError("RC1 monitor must contain all canonical assets")

        usable = tuple(asset for asset in cls.ASSETS
                       if by_asset[asset]["status"] == cls.USABLE_STATUS)
        degraded = tuple(asset for asset in cls.ASSETS
                         if by_asset[asset]["status"] != cls.USABLE_STATUS)
        return {
            "name": "ExternalMarketObservationalView",
            "version": cls.VERSION,
            "observational_only": True,
            "operational_influence_allowed": False,
            "automatic_activation": False,
            "trading_signal": None,
            "score_adjustment": None,
            "reference_timestamp": source.get("reference_timestamp"),
            "readiness": deepcopy(readiness),
            "data_quality": {
                "usable_assets": list(usable),
                "degraded_assets": list(degraded),
                "usable_count": len(usable),
                "canonical_count": len(cls.ASSETS),
                "complete": len(usable) == len(cls.ASSETS),
            },
            "assets": [by_asset[asset] for asset in cls.ASSETS],
        }


def build_observational_view(monitor: dict[str, Any]) -> dict[str, Any]:
    return ExternalMarketObservationalView.build(monitor)
