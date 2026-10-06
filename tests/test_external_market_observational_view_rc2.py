from __future__ import annotations

import pytest

from external_context.external_market_observational_view_rc2 import build_observational_view


def _monitor() -> dict:
    base = {
        "observational_only": True,
        "operational_influence_allowed": False,
        "automatic_activation": False,
        "reference_timestamp": "2026-10-06T20:41:00+00:00",
        "readiness": {"status": "DATA_NOT_READY", "missing_assets": ["DXY"]},
        "assets": [],
    }
    values = {
        "US500": ("AVAILABLE", 0.59018),
        "NASDAQ": ("AVAILABLE", 0.44576),
        "DXY": ("MISSING", None),
        "VIX": ("AVAILABLE", -3.28608),
        "US10Y": ("MISSING", None),
        "OIL": ("STALE", -2.43),
        "GOLD": ("AVAILABLE", -0.12511522),
    }
    for asset, (status, change) in values.items():
        base["assets"].append({
            "asset": asset, "status": status, "price": 1.0 if change is not None else None,
            "change": change, "timestamp": None, "provider": None,
            "provider_symbol": None, "reasons": [],
        })
    return base


def test_rc2_describes_only_available_asset_direction_and_quality():
    result = build_observational_view(_monitor())
    rows = {row["asset"]: row for row in result["assets"]}
    assert rows["US500"]["observed_direction"] == "POSITIVE"
    assert rows["NASDAQ"]["observed_direction"] == "POSITIVE"
    assert rows["VIX"]["observed_direction"] == "NEGATIVE"
    assert rows["GOLD"]["observed_direction"] == "NEGATIVE"
    assert rows["OIL"]["observed_direction"] == "UNAVAILABLE"
    assert rows["DXY"]["observed_direction"] == "UNAVAILABLE"
    assert rows["US10Y"]["observed_direction"] == "UNAVAILABLE"
    assert result["data_quality"]["usable_count"] == 4
    assert result["data_quality"]["degraded_assets"] == ["DXY", "US10Y", "OIL"]
    assert result["data_quality"]["complete"] is False


def test_rc2_cannot_emit_operational_outputs():
    result = build_observational_view(_monitor())
    assert result["observational_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["automatic_activation"] is False
    assert result["trading_signal"] is None
    assert result["score_adjustment"] is None
    assert result["readiness"]["status"] == "DATA_NOT_READY"


@pytest.mark.parametrize(
    "field,value",
    [
        ("observational_only", False),
        ("operational_influence_allowed", True),
        ("automatic_activation", True),
    ],
)
def test_rc2_fails_closed_if_boundary_is_weakened(field, value):
    source = _monitor()
    source[field] = value
    with pytest.raises(ValueError):
        build_observational_view(source)


def test_rc2_requires_exactly_one_row_per_canonical_asset():
    source = _monitor()
    source["assets"].pop()
    with pytest.raises(ValueError):
        build_observational_view(source)

    source = _monitor()
    source["assets"].append(dict(source["assets"][0]))
    with pytest.raises(ValueError):
        build_observational_view(source)
