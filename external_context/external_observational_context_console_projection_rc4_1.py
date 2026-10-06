"""Read-only console projection for External Observational Context RC4.

Presentation-only boundary. Receives an already-built RC4 context and renders
operator-facing lines. It does not collect data, activate providers, read clocks,
or influence Score/Risk/Decision/Alert/orders.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class ExternalObservationalContextConsoleProjection:
    VERSION = "RC4.1-READONLY"

    @classmethod
    def build(cls, context: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(context, dict):
            raise TypeError("context must be a dict")
        source = deepcopy(context)
        if source.get("name") != "ExternalObservationalContext" or source.get("version") != "RC4":
            raise ValueError("RC4 context required")
        if source.get("observational_only") is not True:
            raise ValueError("observational_only must remain true")
        if source.get("operational_influence_allowed") is not False:
            raise ValueError("operational influence must remain disabled")
        if source.get("automatic_activation") is not False:
            raise ValueError("automatic activation must remain disabled")
        for field in ("win_bias", "trading_signal", "score_adjustment", "confidence"):
            if source.get(field) is not None:
                raise ValueError(f"read-only projection refuses operationalized field: {field}")

        quality = source.get("data_quality")
        readiness = source.get("readiness")
        if not isinstance(quality, dict) or not isinstance(readiness, dict):
            raise ValueError("RC4 readiness and data_quality are required")

        usable = list(quality.get("usable_assets") or [])
        degraded = list(quality.get("degraded_assets") or [])
        stale = set(readiness.get("stale_assets") or [])
        missing = set(readiness.get("missing_assets") or [])
        unavailable_required = {
            item.get("asset")
            for item in (source.get("unavailable_context") or [])
            if isinstance(item, dict)
        }

        asset_rows = []
        canonical = ["US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD"]
        for asset in canonical:
            if asset in stale:
                status = "STALE"
            elif asset in missing:
                status = "MISSING"
            elif asset in usable:
                status = "AVAILABLE"
            elif asset in degraded or asset in unavailable_required:
                status = "DEGRADED"
            else:
                status = "UNAVAILABLE"
            asset_rows.append({"asset": asset, "status": status})

        labels = [
            item.get("context_label")
            for item in (source.get("context_labels") or [])
            if isinstance(item, dict) and item.get("context_label")
        ]
        lines = [
            f"CONTEXTO EXTERNO: {source.get('context_status', 'UNKNOWN')}",
            f"READINESS: {readiness.get('status', 'UNKNOWN')}",
            f"CONTEXTO UTILIZAVEL: {quality.get('usable_count', len(usable))}/{quality.get('canonical_count', 7)}",
            "INFLUENCIA OPERACIONAL: DESATIVADA",
        ]
        lines.extend(f"{row['asset']}: {row['status']}" for row in asset_rows)
        lines.extend(f"OBSERVACAO: {label}" for label in labels)

        return {
            "name": "ExternalObservationalContextConsoleProjection",
            "version": cls.VERSION,
            "read_only": True,
            "operational_influence_allowed": False,
            "automatic_activation": False,
            "context_status": source.get("context_status"),
            "readiness_status": readiness.get("status"),
            "usable_count": quality.get("usable_count", len(usable)),
            "canonical_count": quality.get("canonical_count", 7),
            "asset_rows": asset_rows,
            "context_labels": labels,
            "lines": lines,
        }


def build_console_projection(context: dict[str, Any]) -> dict[str, Any]:
    return ExternalObservationalContextConsoleProjection.build(context)
