from __future__ import annotations

import pytest

from external_context.external_observational_context_rc4 import build_observational_context


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


def test_rc4_translates_rc3_without_creating_win_bias_or_signal():
    result = build_observational_context(_synthesis())
    labels = {item["relationship"]: item["context_label"] for item in result["context_labels"]}
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


def test_rc4_full_context_requires_rc3_complete_status():
    source = _synthesis()
    source["synthesis_status"] = "COMPLETE"
    source["missing_required_context"] = []
    result = build_observational_context(source)
    assert result["context_status"] == "FULL_CONTEXT"
    assert result["unavailable_context"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("observational_only", False),
        ("operational_influence_allowed", True),
        ("automatic_activation", True),
        ("trading_signal", "BUY"),
        ("score_adjustment", 1),
        ("confidence", 0.8),
    ],
)
def test_rc4_fails_closed_if_boundary_is_weakened(field, value):
    source = _synthesis()
    source[field] = value
    with pytest.raises(ValueError):
        build_observational_context(source)


def test_rc4_rejects_unknown_observational_relationship_state():
    source = _synthesis()
    source["observations"][0]["state"] = "BULLISH"
    with pytest.raises(ValueError):
        build_observational_context(source)
