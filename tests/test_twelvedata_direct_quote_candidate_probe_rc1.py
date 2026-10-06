"""Contract tests for Twelve Data direct quote candidate probe RC1."""
import json

import pytest

from tools.twelvedata_direct_quote_candidate_probe_rc1 import CANDIDATES, run


class Response:
    def __init__(self, payload):
        self.payload = payload
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="TWELVE_DATA_API_KEY"):
        run("")


def test_candidate_set_is_explicit_and_not_declared_approved():
    assert tuple(CANDIDATES) == ("US500", "NASDAQ", "DXY", "VIX", "US10Y", "OIL", "GOLD")


def test_probe_preserves_identity_and_timestamp_evidence_without_key_leak():
    def opener(request, timeout):
        return Response({
            "symbol": "SPX",
            "name": "S&P 500",
            "exchange": "INDEX",
            "datetime": "2026-10-06 12:00:00",
            "timestamp": 1791298800,
            "close": "6000.00",
            "percent_change": "0.25",
        })

    result = run("secret-test-key", opener=opener)
    rendered = json.dumps(result)
    assert result["candidate_aliases_are_approved_mappings"] is False
    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert "secret-test-key" not in rendered
    assert all(item["probe_status"] == "QUOTE_RETURNED" for item in result["results"])
    assert result["results"][0]["provider_fields"]["symbol"] == "SPX"
    assert result["results"][0]["provider_fields"]["datetime"] == "2026-10-06 12:00:00"
    assert result["results"][0]["provider_fields"]["timestamp"] == 1791298800
