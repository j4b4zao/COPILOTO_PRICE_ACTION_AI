from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.external_market_manual_live_view_rc2 import run


def _monitor_result() -> dict:
    values = {
        "US500": ("AVAILABLE", 0.59),
        "NASDAQ": ("AVAILABLE", 0.44),
        "DXY": ("MISSING", None),
        "VIX": ("AVAILABLE", -3.28),
        "US10Y": ("MISSING", None),
        "OIL": ("STALE", -2.43),
        "GOLD": ("AVAILABLE", -0.12),
    }
    return {
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "reference_timestamp": "2026-10-06T20:41:00+00:00",
        "readiness": {"status": "DATA_NOT_READY", "missing_assets": ["DXY"]},
        "assets": [
            {
                "asset": asset, "status": status,
                "price": 1.0 if change is not None else None, "change": change,
                "timestamp": None, "provider": None, "provider_symbol": None,
                "reasons": [],
            }
            for asset, (status, change) in values.items()
        ],
    }


def test_manual_live_view_composes_monitor_into_rc2_without_operational_output():
    with patch(
        "tools.external_market_manual_live_view_rc2.run_monitor",
        return_value=_monitor_result(),
    ) as monitor:
        result = run(
            enabled=True,
            reference_timestamp="2026-10-06T20:41:00+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )

    monitor.assert_called_once()
    assert result["name"] == "ExternalMarketObservationalView"
    assert result["version"] == "RC2"
    assert result["operational_influence_allowed"] is False
    assert result["trading_signal"] is None
    assert result["score_adjustment"] is None
    assert result["data_quality"]["usable_count"] == 4
    assert result["data_quality"]["complete"] is False


def test_manual_live_view_preserves_enable_gate():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T20:41:00+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )
