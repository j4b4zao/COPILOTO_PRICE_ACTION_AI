"""Contract tests for Twelve Data raw catalog shape probe RC1."""
import json

import pytest

from tools.twelvedata_raw_catalog_shape_probe_rc1 import run


class Response:
    def __init__(self, payload):
        self.payload = payload
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_requires_explicit_api_key():
    with pytest.raises(ValueError, match="TWELVE_DATA_API_KEY"):
        run("")


def test_reports_real_payload_shape_without_mapping_or_key_leak():
    payloads = iter([
        {"data": [{"symbol": "SPX", "name": "S&P 500"}], "status": "ok"},
        {"result": {"list": [{"symbol": "US10Y", "name": "US Treasury 10Y"}]}, "status": "ok"},
    ])
    def opener(request, timeout):
        return Response(next(payloads))

    result = run("secret-test-key", opener=opener)
    rendered = json.dumps(result)

    assert result["creates_provider_symbol_map"] is False
    assert result["creates_manifest"] is False
    assert "secret-test-key" not in rendered
    assert result["results"][0]["payload_shape"]["type"] == "dict"
    assert result["results"][1]["payload_shape"]["type"] == "dict"
    assert result["results"][0]["sanitized_sample"]["data"][0]["symbol"] == "SPX"
    assert result["results"][1]["sanitized_sample"]["result"]["list"][0]["symbol"] == "US10Y"
