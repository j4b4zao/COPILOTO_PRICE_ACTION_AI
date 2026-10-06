from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.external_observational_manual_console_rc4_1 import run


def _context() -> dict:
    return {
        "name": "ExternalObservationalContext",
        "version": "RC4",
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "win_bias": None,
        "trading_signal": None,
        "score_adjustment": None,
        "confidence": None,
        "context_status": "PARTIAL_CONTEXT",
        "missing_required_context": ["US500", "NASDAQ", "DXY"],
        "context_labels": [],
        "unavailable_context": [
            {"asset": "US500", "context_label": "US500_CONTEXT_UNAVAILABLE"},
            {"asset": "NASDAQ", "context_label": "NASDAQ_CONTEXT_UNAVAILABLE"},
            {"asset": "DXY", "context_label": "DXY_CONTEXT_UNAVAILABLE"},
        ],
        "readiness": {
            "status": "DATA_NOT_READY",
            "available_assets": ["US500", "NASDAQ", "VIX"],
            "missing_assets": ["DXY"],
            "stale_assets": ["US500", "NASDAQ"],
            "maximum_observed_skew_seconds": 3761.0,
        },
        "data_quality": {
            "usable_assets": ["VIX"],
            "degraded_assets": ["US500", "NASDAQ", "DXY", "US10Y", "OIL", "GOLD"],
            "usable_count": 1,
            "canonical_count": 7,
            "complete": False,
        },
    }


def test_manual_console_rc4_1_composes_rc4_into_read_only_projection():
    with patch(
        "tools.external_observational_manual_console_rc4_1.run_context",
        return_value=_context(),
    ) as context:
        result = run(
            enabled=True,
            reference_timestamp="2026-10-06T21:03:09+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )

    context.assert_called_once()
    rows = {row["asset"]: row["status"] for row in result["asset_rows"]}
    assert result["name"] == "ExternalObservationalContextConsoleProjection"
    assert result["version"] == "RC4.1-READONLY"
    assert result["read_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["context_status"] == "PARTIAL_CONTEXT"
    assert result["usable_count"] == 1
    assert rows["US500"] == "STALE"
    assert rows["NASDAQ"] == "STALE"
    assert rows["DXY"] == "MISSING"
    assert rows["VIX"] == "AVAILABLE"
    assert "INFLUENCIA OPERACIONAL: DESATIVADA" in result["lines"]


def test_manual_console_rc4_1_preserves_enable_gate():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T21:03:09+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )
