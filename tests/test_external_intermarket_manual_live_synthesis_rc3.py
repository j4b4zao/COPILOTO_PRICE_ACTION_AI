from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.external_intermarket_manual_live_synthesis_rc3 import run


def _view() -> dict:
    directions = {
        "US500": "POSITIVE", "NASDAQ": "POSITIVE", "DXY": "UNAVAILABLE",
        "VIX": "NEGATIVE", "US10Y": "UNAVAILABLE", "OIL": "UNAVAILABLE",
        "GOLD": "NEGATIVE",
    }
    return {
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "trading_signal": None,
        "score_adjustment": None,
        "readiness": {"status": "DATA_NOT_READY", "missing_assets": ["DXY"]},
        "data_quality": {"usable_count": 4, "canonical_count": 7, "complete": False},
        "assets": [
            {"asset": asset, "observed_direction": direction}
            for asset, direction in directions.items()
        ],
    }


def test_manual_live_rc3_composes_rc2_view_into_synthesis():
    with patch(
        "tools.external_intermarket_manual_live_synthesis_rc3.run_view",
        return_value=_view(),
    ) as view:
        result = run(
            enabled=True,
            reference_timestamp="2026-10-06T20:46:48+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )

    view.assert_called_once()
    assert result["name"] == "ExternalIntermarketObservationalSynthesis"
    assert result["version"] == "RC3"
    assert result["synthesis_status"] == "INCOMPLETE"
    assert result["missing_required_context"] == ["DXY"]
    assert result["operational_influence_allowed"] is False
    assert result["trading_signal"] is None
    assert result["score_adjustment"] is None
    assert result["confidence"] is None


def test_manual_live_rc3_preserves_enable_gate():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T20:46:48+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )
