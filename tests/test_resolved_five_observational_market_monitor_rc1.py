from __future__ import annotations

import pytest

from external_context.resolved_five_observational_market_monitor import (
    ResolvedFiveObservationalMarketMonitor,
    build_monitor,
)


def _activation() -> dict:
    return {
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "reference_timestamp": "2026-10-06T20:29:35+00:00",
        "maximum_staleness_seconds": 3600.0,
        "collector_state_valid": False,
        "collector_reasons": ["DXY inválido ou ausente."],
        "readiness": {
            "status": "DATA_NOT_READY",
            "available_assets": ["US500", "NASDAQ", "VIX"],
            "missing_assets": ["DXY"],
            "stale_assets": [],
            "maximum_observed_skew_seconds": 1776.0,
        },
        "assets": {
            "US500": {"status": "AVAILABLE", "price": 7819.83, "change": 0.59018,
                      "timestamp": "2026-10-06T19:59:59+00:00", "provider": "FMP",
                      "provider_symbol": "^GSPC", "reasons": []},
            "NASDAQ": {"status": "AVAILABLE", "price": 27599.7918, "change": 0.44576,
                       "timestamp": "2026-10-06T20:00:07+00:00", "provider": "FMP",
                       "provider_symbol": "^IXIC", "reasons": []},
            "DXY": {"status": "MISSING", "price": None, "change": None, "timestamp": None,
                    "provider": None, "provider_symbol": None,
                    "reasons": ["INVALID_TIMESTAMP", "INVALID_QUOTE"]},
            "VIX": {"status": "AVAILABLE", "price": 15.01, "change": -3.28608,
                    "timestamp": "2026-10-06T20:13:16+00:00", "provider": "FMP",
                    "provider_symbol": "^VIX", "reasons": []},
            "US10Y": {"status": "MISSING", "price": None, "change": None, "timestamp": None,
                      "provider": None, "provider_symbol": None,
                      "reasons": ["INVALID_TIMESTAMP", "INVALID_QUOTE"]},
            "OIL": {"status": "STALE", "price": 87.26, "change": -2.43,
                    "timestamp": "2026-10-06T13:02:49+00:00",
                    "provider": "Americas Oil Watch / Yahoo Finance CL=F",
                    "provider_symbol": "CL=F", "reasons": []},
            "GOLD": {"status": "AVAILABLE", "price": 4162.87411, "change": -0.15625359,
                     "timestamp": "2026-10-06T20:00:00+00:00", "provider": "Twelve Data",
                     "provider_symbol": "XAU/USD", "reasons": []},
        },
    }


def test_monitor_preserves_observational_boundary_and_quality_labels():
    result = build_monitor(_activation())
    assert result["observational_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["automatic_activation"] is False
    assert result["readiness"]["status"] == "DATA_NOT_READY"
    assert result["readiness"]["missing_assets"] == ["DXY"]
    assert result["status_counts"]["AVAILABLE"] == 4
    assert result["status_counts"]["STALE"] == 1
    assert result["status_counts"]["MISSING"] == 2
    rows = {row["asset"]: row for row in result["assets"]}
    assert rows["DXY"]["configured"] is False
    assert rows["US10Y"]["configured"] is False
    assert rows["OIL"]["status"] == "STALE"
    assert rows["GOLD"]["status"] == "AVAILABLE"


def test_monitor_is_detached_from_input():
    source = _activation()
    result = build_monitor(source)
    result["assets"][0]["price"] = -1
    result["readiness"]["missing_assets"].append("US500")
    assert source["assets"]["US500"]["price"] == 7819.83
    assert source["readiness"]["missing_assets"] == ["DXY"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("observational_only", False),
        ("operational_influence_allowed", True),
        ("automatic_activation", True),
    ],
)
def test_monitor_fails_closed_if_safety_boundary_is_weakened(field, value):
    source = _activation()
    source[field] = value
    with pytest.raises(ValueError):
        ResolvedFiveObservationalMarketMonitor.build(source)


def test_monitor_rejects_unknown_asset_and_status():
    source = _activation()
    source["assets"]["BTC"] = {"status": "AVAILABLE"}
    with pytest.raises(ValueError):
        build_monitor(source)

    source = _activation()
    source["assets"]["US500"]["status"] = "BUY"
    with pytest.raises(ValueError):
        build_monitor(source)
