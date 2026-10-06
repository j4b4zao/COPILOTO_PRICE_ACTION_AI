"""Contract tests for manual FMP real market probe RC1."""
import json

import pytest

from tools.fmp_real_market_probe_rc1 import CANDIDATES, run


class Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="FMP_API_KEY"):
        run("")


def test_candidate_scope_is_explicit_and_us10y_is_not_guessed():
    assert tuple(CANDIDATES) == ("US500", "NASDAQ", "DXY", "VIX", "OIL")
    assert "US10Y" not in CANDIDATES


def test_probe_is_observational_and_does_not_promote_candidates():
    def opener(request, timeout):
        return Response([{
            "symbol": "^GSPC",
            "name": "S&P 500",
            "price": 6000.0,
            "change": 10.0,
            "changePercentage": 0.17,
            "timestamp": 1791298800,
            "exchange": "INDEX",
        }])

    result = run("secret-fmp-key", opener=opener)
    rendered = json.dumps(result)

    assert result["observational_only"] is True
    assert result["candidate_aliases_are_approved_mappings"] is False
    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert result["creates_router_routes"] is False
    assert result["us10y_intentionally_excluded"] is True
    assert "secret-fmp-key" not in rendered
    assert all(item["probe_status"] == "QUOTE_RETURNED" for item in result["results"])
    assert result["results"][0]["provider_fields"]["timestamp"] == 1791298800


def test_empty_provider_list_fails_closed():
    result = run("test-key", opener=lambda request, timeout: Response([]))
    assert all(item["probe_status"] == "INVALID_OR_EMPTY_PAYLOAD" for item in result["results"])
