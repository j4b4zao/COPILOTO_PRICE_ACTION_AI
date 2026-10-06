"""External intermarket observational synthesis RC3.

Presentation/research-only synthesis over RC2. It describes observable relationships
without producing trading direction, score, confidence, risk, decision, alert, or order.
Missing required context remains explicit and prevents a COMPLETE synthesis.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class ExternalIntermarketObservationalSynthesis:
    VERSION = "RC3"
    REQUIRED_CONTEXT = ("US500", "NASDAQ", "DXY", "VIX")

    @classmethod
    def build(cls, view: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(view, dict):
            raise TypeError("view must be a dict")
        source = deepcopy(view)
        if source.get("observational_only") is not True:
            raise ValueError("RC3 accepts observational data only")
        if source.get("operational_influence_allowed") is not False:
            raise ValueError("operational influence must remain disabled")
        if source.get("automatic_activation") is not False:
            raise ValueError("automatic activation must remain disabled")
        if source.get("trading_signal") is not None or source.get("score_adjustment") is not None:
            raise ValueError("RC3 refuses operationalized RC2 input")

        rows = source.get("assets")
        if not isinstance(rows, list):
            raise ValueError("invalid RC2 asset contract")
        assets = {}
        for row in rows:
            if not isinstance(row, dict) or not row.get("asset"):
                raise ValueError("invalid RC2 asset row")
            asset = row["asset"]
            if asset in assets:
                raise ValueError("duplicate RC2 asset")
            assets[asset] = row

        missing_required = [
            asset for asset in cls.REQUIRED_CONTEXT
            if assets.get(asset, {}).get("observed_direction") == "UNAVAILABLE"
        ]
        observations = []

        us500 = assets.get("US500", {}).get("observed_direction")
        nasdaq = assets.get("NASDAQ", {}).get("observed_direction")
        vix = assets.get("VIX", {}).get("observed_direction")
        if us500 in {"POSITIVE", "NEGATIVE", "FLAT"} and nasdaq in {"POSITIVE", "NEGATIVE", "FLAT"}:
            observations.append({
                "relationship": "US_EQUITIES",
                "state": "ALIGNED" if us500 == nasdaq else "MIXED",
                "components": {"US500": us500, "NASDAQ": nasdaq},
            })
        if us500 in {"POSITIVE", "NEGATIVE"} and vix in {"POSITIVE", "NEGATIVE"}:
            expected_vix = "NEGATIVE" if us500 == "POSITIVE" else "POSITIVE"
            observations.append({
                "relationship": "US500_VIX",
                "state": "INVERSE_ALIGNMENT" if vix == expected_vix else "NON_INVERSE",
                "components": {"US500": us500, "VIX": vix},
            })

        return {
            "name": "ExternalIntermarketObservationalSynthesis",
            "version": cls.VERSION,
            "observational_only": True,
            "operational_influence_allowed": False,
            "automatic_activation": False,
            "trading_signal": None,
            "score_adjustment": None,
            "confidence": None,
            "synthesis_status": "INCOMPLETE" if missing_required else "COMPLETE",
            "missing_required_context": missing_required,
            "readiness": deepcopy(source.get("readiness")),
            "data_quality": deepcopy(source.get("data_quality")),
            "observations": observations,
        }


def build_observational_synthesis(view: dict[str, Any]) -> dict[str, Any]:
    return ExternalIntermarketObservationalSynthesis.build(view)
