"""Observational external market monitor presentation RC1.

Pure presentation over an already-produced manual live activation result.
No provider calls, environment reads, clock reads, thresholds, scoring, risk,
decision, alert, order logic, or automatic activation are owned here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class ResolvedFiveObservationalMarketMonitor:
    VERSION = "RC1"
    CANONICAL_ASSETS = ("US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD")
    CONFIGURED_ASSETS = ("US500", "NASDAQ", "VIX", "OIL", "GOLD")
    STATUS_VALUES = {"AVAILABLE", "STALE", "MISSING", "FUTURE", "INVALID"}

    @classmethod
    def build(cls, activation_result: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(activation_result, dict):
            raise TypeError("activation_result must be a dict")
        source = deepcopy(activation_result)
        if source.get("observational_only") is not True:
            raise ValueError("monitor accepts observational activation results only")
        if source.get("operational_influence_allowed") is not False:
            raise ValueError("operational influence must remain disabled")
        if source.get("automatic_activation") is not False:
            raise ValueError("automatic activation must remain disabled")

        readiness = source.get("readiness")
        assets = source.get("assets")
        if not isinstance(readiness, dict) or not isinstance(assets, dict):
            raise ValueError("activation result lacks readiness/assets contract")
        extras = set(assets) - set(cls.CANONICAL_ASSETS)
        if extras:
            raise ValueError("unsupported assets in activation result")

        rows = []
        counts = {status: 0 for status in sorted(cls.STATUS_VALUES)}
        for canonical in cls.CANONICAL_ASSETS:
            raw = assets.get(canonical)
            if not isinstance(raw, dict):
                raw = {
                    "status": "MISSING", "price": None, "change": None,
                    "timestamp": None, "provider": None, "provider_symbol": None,
                    "reasons": ["NOT_PRESENT_IN_ACTIVATION_RESULT"],
                }
            status = raw.get("status")
            if status not in cls.STATUS_VALUES:
                raise ValueError(f"unsupported status for {canonical}: {status!r}")
            counts[status] += 1
            rows.append({
                "asset": canonical,
                "configured": canonical in cls.CONFIGURED_ASSETS,
                "status": status,
                "price": raw.get("price"),
                "change": raw.get("change"),
                "timestamp": raw.get("timestamp"),
                "provider": raw.get("provider"),
                "provider_symbol": raw.get("provider_symbol"),
                "reasons": list(raw.get("reasons") or ()),
            })

        return {
            "name": "ResolvedFiveObservationalMarketMonitor",
            "version": cls.VERSION,
            "observational_only": True,
            "operational_influence_allowed": False,
            "automatic_activation": False,
            "reference_timestamp": source.get("reference_timestamp"),
            "maximum_staleness_seconds": source.get("maximum_staleness_seconds"),
            "readiness": deepcopy(readiness),
            "collector_state_valid": source.get("collector_state_valid"),
            "collector_reasons": list(source.get("collector_reasons") or ()),
            "status_counts": counts,
            "assets": rows,
        }


def build_monitor(activation_result: dict[str, Any]) -> dict[str, Any]:
    return ResolvedFiveObservationalMarketMonitor.build(activation_result)
