"""Offline contract tests for Finnhub real catalog probe RC1."""
import json

import pytest

from tools.finnhub_real_catalog_probe_rc1 import run


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._raw


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
        run("")


def test_catalog_probe_finds_evidence_without_approving_mapping():
    def opener(request, timeout):
        if "/forex/exchange" in request.full_url:
            return Response(["oanda"])
        return Response([
            {
                "description": "Example US Dollar Index",
                "displaySymbol": "DXY",
                "symbol": "OANDA:DXY",
            },
            {
                "description": "Example WTI Crude Oil",
                "displaySymbol": "WTI/USD",
                "symbol": "OANDA:WTI_USD",
            },
        ])

    result = run("secret-key", opener=opener)
    rendered = json.dumps(result)

    assert result["observational_only"] is True
    assert result["candidate_aliases_are_approved_mappings"] is False
    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert result["creates_router_routes"] is False
    assert result["matches"]["DXY"][0]["symbol"] == "OANDA:DXY"
    assert result["matches"]["OIL"][0]["symbol"] == "OANDA:WTI_USD"
    assert result["US10Y"]["status"] == "NOT_PROBED_AS_INTRADAY"
    assert "secret-key" not in rendered


def test_empty_exchange_catalog_fails_closed_without_guessing():
    result = run("key", opener=lambda request, timeout: Response([]))
    assert result["forex_exchange_status"] == "UNAVAILABLE"
    assert result["matches"] == {"DXY": [], "OIL": []}
    assert result["candidate_aliases_are_approved_mappings"] is False
