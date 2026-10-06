from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.resolved_five_manual_live_monitor_rc1 import run


def _activation_result() -> dict:
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
                    "provider": None, "provider_symbol": None, "reasons": []},
            "VIX": {"status": "AVAILABLE", "price": 15.01, "change": -3.28608,
                    "timestamp": "2026-10-06T20:13:16+00:00", "provider": "FMP",
                    "provider_symbol": "^VIX", "reasons": []},
            "US10Y": {"status": "MISSING", "price": None, "change": None, "timestamp": None,
                      "provider": None, "provider_symbol": None, "reasons": []},
            "OIL": {"status": "STALE", "price": 87.26, "change": -2.43,
                    "timestamp": "2026-10-06T13:02:49+00:00",
                    "provider": "Americas Oil Watch / Yahoo Finance CL=F",
                    "provider_symbol": "CL=F", "reasons": []},
            "GOLD": {"status": "AVAILABLE", "price": 4162.87411, "change": -0.15625359,
                     "timestamp": "2026-10-06T20:00:00+00:00", "provider": "Twelve Data",
                     "provider_symbol": "XAU/USD", "reasons": []},
        },
    }


def test_runner_delegates_activation_to_observational_monitor():
    with patch(
        "tools.resolved_five_manual_live_monitor_rc1.run_activation",
        return_value=_activation_result(),
    ) as activation:
        result = run(
            enabled=True,
            reference_timestamp="2026-10-06T20:29:35+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )

    activation.assert_called_once()
    assert result["name"] == "ResolvedFiveObservationalMarketMonitor"
    assert result["observational_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["automatic_activation"] is False
    assert result["readiness"]["status"] == "DATA_NOT_READY"
    assert result["status_counts"]["AVAILABLE"] == 4
    assert result["status_counts"]["STALE"] == 1
    assert result["status_counts"]["MISSING"] == 2


def test_runner_does_not_bypass_manual_enable_gate():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T20:29:35+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )
