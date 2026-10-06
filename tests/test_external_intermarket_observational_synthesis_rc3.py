from __future__ import annotations

import pytest

from external_context.external_intermarket_observational_synthesis_rc3 import (
    build_observational_synthesis,
)


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


def test_rc3_describes_real_shape_without_trading_output():
    result = build_observational_synthesis(_view())
    observations = {item["relationship"]: item for item in result["observations"]}
    assert result["synthesis_status"] == "INCOMPLETE"
    assert result["missing_required_context"] == ["DXY"]
    assert observations["US_EQUITIES"]["state"] == "ALIGNED"
    assert observations["US500_VIX"]["state"] == "INVERSE_ALIGNMENT"
    assert result["trading_signal"] is None
    assert result["score_adjustment"] is None
    assert result["confidence"] is None
    assert result["operational_influence_allowed"] is False


def test_rc3_becomes_complete_only_when_all_required_context_is_available():
    source = _view()
    for row in source["assets"]:
        if row["asset"] == "DXY":
            row["observed_direction"] = "NEGATIVE"
    result = build_observational_synthesis(source)
    assert result["synthesis_status"] == "COMPLETE"
    assert result["missing_required_context"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("observational_only", False),
        ("operational_influence_allowed", True),
        ("automatic_activation", True),
        ("trading_signal", "BUY"),
        ("score_adjustment", 1),
    ],
)
def test_rc3_fails_closed_if_observational_boundary_is_weakened(field, value):
    source = _view()
    source[field] = value
    with pytest.raises(ValueError):
        build_observational_synthesis(source)
