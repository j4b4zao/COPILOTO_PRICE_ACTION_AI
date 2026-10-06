from __future__ import annotations

from unittest.mock import patch

import pytest

from tools.external_observational_manual_live_context_rc4 import run


def _synthesis() -> dict:
    return {
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "trading_signal": None,
        "score_adjustment": None,
        "confidence": None,
        "synthesis_status": "INCOMPLETE",
        "missing_required_context": ["DXY"],
        "readiness": {"status": "DATA_NOT_READY", "missing_assets": ["DXY"]},
        "data_quality": {"usable_count": 4, "canonical_count": 7, "complete": False},
        "observations": [
            {
                "relationship": "US_EQUITIES",
                "state": "ALIGNED",
                "components": {"US500": "POSITIVE", "NASDAQ": "POSITIVE"},
            },
            {
                "relationship": "US500_VIX",
                "state": "INVERSE_ALIGNMENT",
                "components": {"US500": "POSITIVE", "VIX": "NEGATIVE"},
            },
        ],
    }


def test_manual_live_rc4_composes_rc3_into_semantic_context():
    with patch(
        "tools.external_observational_manual_live_context_rc4.run_synthesis",
        return_value=_synthesis(),
    ) as synthesis:
        result = run(
            enabled=True,
            reference_timestamp="2026-10-06T20:46:48+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )

    synthesis.assert_called_once()
    labels = {x["relationship"]: x["context_label"] for x in result["context_labels"]}
    assert result["context_status"] == "PARTIAL_CONTEXT"
    assert result["missing_required_context"] == ["DXY"]
    assert labels["US_EQUITIES"] == "EQUITIES_ALIGNED"
    assert labels["US500_VIX"] == "VOLATILITY_INVERSE_ALIGNMENT"
    assert result["unavailable_context"] == [
        {"asset": "DXY", "context_label": "DXY_CONTEXT_UNAVAILABLE"}
    ]
    assert result["win_bias"] is None
    assert result["trading_signal"] is None
    assert result["score_adjustment"] is None
    assert result["confidence"] is None
    assert result["operational_influence_allowed"] is False


def test_manual_live_rc4_preserves_enable_gate():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T20:46:48+00:00",
            maximum_staleness_seconds=3600.0,
            fmp_api_key="fmp-test",
            twelvedata_api_key="td-test",
        )
