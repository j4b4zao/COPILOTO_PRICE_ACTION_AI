"""Offline contract tests for Finnhub real quote candidate probe RC1."""
import json

import pytest

from tools.finnhub_real_quote_candidate_probe_rc1 import CANDIDATES, run


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")
    def read(self):
        return self._raw


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="FINNHUB_API_KEY"):
        run("")


def test_candidates_are_catalog_evidence_but_not_approved_mappings():
    assert CANDIDATES == {
        "DXY": "CAPITAL:DXY",
        "OIL": "OANDA:WTICO_USD",
    }

    def opener(request, timeout):
        return Response({
            "c": 100.25,
            "d": 0.1,
            "dp": 0.1,
            "h": 101,
            "l": 99,
            "o": 100,
            "pc": 100.15,
            "t": 1791311985,
        })

    result = run("secret-key", opener=opener)
    rendered = json.dumps(result)
    assert result["candidate_aliases_are_approved_mappings"] is False
    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert result["creates_router_routes"] is False
    assert all(item["probe_status"] == "QUOTE_RETURNED" for item in result["results"])
    assert all(item["provider_fields"]["t"] == 1791311985 for item in result["results"])
    assert "secret-key" not in rendered


def test_zero_quote_fails_closed():
    result = run(
        "key",
        opener=lambda request, timeout: Response({"c": 0, "d": None, "dp": None, "t": 0}),
    )
    assert all(item["probe_status"] == "NO_VALID_QUOTE" for item in result["results"])
