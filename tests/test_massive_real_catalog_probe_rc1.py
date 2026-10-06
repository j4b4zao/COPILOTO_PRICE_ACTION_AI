"""Offline contract tests for Massive real catalog probe RC1."""
import json

import pytest

from tools.massive_real_catalog_probe_rc1 import run


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._raw


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="MASSIVE_API_KEY"):
        run("")


def test_catalog_evidence_is_reported_without_mapping_or_expiry_selection():
    def opener(request, timeout):
        if "/v3/reference/tickers" in request.full_url:
            return Response({"status": "OK", "results": [{
                "ticker": "I:EXAMPLE",
                "name": "US Dollar Index",
                "market": "indices",
                "active": True,
            }]})
        return Response({"status": "OK", "results": [{
            "product_code": "CL",
            "name": "WTI Crude Oil Futures",
            "exchange": "NYMEX",
            "asset_class": "Energy",
        }]})

    result = run("secret-key", opener=opener)
    rendered = json.dumps(result)

    assert result["observational_only"] is True
    assert result["candidate_aliases_are_approved_mappings"] is False
    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert result["creates_router_routes"] is False
    assert result["selects_futures_expiry"] is False
    assert result["DXY"]["matches"][0]["name"] == "US Dollar Index"
    assert result["OIL"]["matches"][0]["product_code"] == "CL"
    assert result["US10Y"]["status"] == "NOT_PROBED_AS_INTRADAY"
    assert "secret-key" not in rendered


def test_empty_or_unavailable_catalog_fails_closed():
    def opener(request, timeout):
        return Response({"status": "OK", "results": []})

    result = run("key", opener=opener)
    assert result["DXY"]["matches"] == []
    assert result["OIL"]["matches"] == []
    assert result["candidate_aliases_are_approved_mappings"] is False
