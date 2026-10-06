from __future__ import annotations

import pytest

from external_context.external_observational_context_console_projection_rc4_1 import (
    build_console_projection,
)


def _real_degraded_shape() -> dict:
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


def test_projection_matches_real_degraded_rc4_shape():
    result = build_console_projection(_real_degraded_shape())
    rows = {row["asset"]: row["status"] for row in result["asset_rows"]}
    assert result["read_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["context_status"] == "PARTIAL_CONTEXT"
    assert result["readiness_status"] == "DATA_NOT_READY"
    assert result["usable_count"] == 1
    assert result["canonical_count"] == 7
    assert rows["US500"] == "STALE"
    assert rows["NASDAQ"] == "STALE"
    assert rows["DXY"] == "MISSING"
    assert rows["VIX"] == "AVAILABLE"
    assert "INFLUENCIA OPERACIONAL: DESATIVADA" in result["lines"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("observational_only", False),
        ("operational_influence_allowed", True),
        ("automatic_activation", True),
        ("win_bias", "BULLISH"),
        ("trading_signal", "BUY"),
        ("score_adjustment", 1),
        ("confidence", 0.8),
    ],
)
def test_projection_fails_closed_if_rc4_boundary_is_weakened(field, value):
    source = _real_degraded_shape()
    source[field] = value
    with pytest.raises(ValueError):
        build_console_projection(source)


def test_projection_does_not_mutate_source():
    source = _real_degraded_shape()
    before = repr(source)
    build_console_projection(source)
    assert repr(source) == before
