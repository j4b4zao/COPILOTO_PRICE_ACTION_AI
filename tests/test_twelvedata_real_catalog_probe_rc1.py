"""Contract tests for the Twelve Data real catalog probe RC1."""
import json
from urllib.parse import parse_qs, urlparse

import pytest

from tools.twelvedata_real_catalog_probe_rc1 import PROBES, run


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="TWELVE_DATA_API_KEY"):
        run("")


def test_probe_uses_indices_for_four_assets_and_bonds_for_us10y():
    assert PROBES == (
        ("US500", "indices", {"country": "United States"}),
        ("NASDAQ", "indices", {"country": "United States"}),
        ("DXY", "indices", {"country": "United States"}),
        ("VIX", "indices", {"country": "United States"}),
        ("US10Y", "bonds", {"country": "United States"}),
    )


def test_probe_reports_matches_without_promoting_them():
    seen = []

    def opener(request, timeout):
        parsed = urlparse(request.full_url)
        seen.append((parsed.path, parse_qs(parsed.query)))
        if parsed.path.endswith("/bonds"):
            return Response({"result": {"list": [
                {"symbol": "US10Y", "name": "US Treasury Yield 10 Years", "type": "Bond"}
            ]}, "status": "ok"})
        return Response({"data": [
            {"symbol": "SPX", "name": "S&P 500", "type": "Index"},
            {"symbol": "IXIC", "name": "Nasdaq Composite", "type": "Index"},
            {"symbol": "DXY", "name": "US Dollar Index", "type": "Index"},
            {"symbol": "VIX", "name": "CBOE Volatility Index", "type": "Index"},
        ], "status": "ok"})

    result = run("offline-key", opener=opener)

    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert len(seen) == 5
    by_asset = {item["internal_asset"]: item for item in result["results"]}
    assert by_asset["US500"]["matches"][0]["symbol"] == "SPX"
    assert by_asset["NASDAQ"]["matches"][0]["symbol"] == "IXIC"
    assert by_asset["DXY"]["matches"][0]["symbol"] == "DXY"
    assert by_asset["VIX"]["matches"][0]["symbol"] == "VIX"
    assert by_asset["US10Y"]["matches"][0]["symbol"] == "US10Y"
