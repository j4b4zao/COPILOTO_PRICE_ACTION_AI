import json

from external_context.providers.http_json_provider import (
    HttpJsonExternalMarketProvider,
    HttpJsonSymbolConfig,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _opener(payload):
    def open_(request, timeout):
        return _Response(payload)
    return open_


def test_fetch_simple_payload():
    provider = HttpJsonExternalMarketProvider(
        {"US500": HttpJsonSymbolConfig("https://x")},
        opener=_opener({"price": 6500, "change": 0.5, "timestamp": "2026-08-23T14:00:00"}),
    )
    result = provider.fetch("US500")
    assert result["price"] == 6500.0
    assert result["change"] == 0.5


def test_fetch_nested_payload():
    provider = HttpJsonExternalMarketProvider(
        {"NASDAQ": HttpJsonSymbolConfig("https://x", "data.quote.price", "data.quote.change", "data.time")},
        opener=_opener({"data": {"quote": {"price": 23000, "change": -0.2}, "time": "t"}}),
    )
    assert provider.fetch("NASDAQ") == {"price": 23000.0, "change": -0.2, "timestamp": "t"}


def test_fetch_list_path():
    provider = HttpJsonExternalMarketProvider(
        {"DXY": HttpJsonSymbolConfig("https://x", "data.0.price", "data.0.change", "data.0.timestamp")},
        opener=_opener({"data": [{"price": 98.2, "change": 0.1, "timestamp": "t"}]}),
    )
    assert provider.fetch("DXY")["price"] == 98.2


def test_missing_symbol_returns_none():
    provider = HttpJsonExternalMarketProvider({}, opener=_opener({}))
    assert provider.fetch("VIX") is None


def test_invalid_price_returns_none():
    provider = HttpJsonExternalMarketProvider(
        {"VIX": HttpJsonSymbolConfig("https://x")},
        opener=_opener({"price": "bad", "change": 1, "timestamp": "t"}),
    )
    assert provider.fetch("VIX") is None


def test_non_positive_price_returns_none():
    provider = HttpJsonExternalMarketProvider(
        {"OIL": HttpJsonSymbolConfig("https://x")},
        opener=_opener({"price": 0, "change": 1, "timestamp": "t"}),
    )
    assert provider.fetch("OIL") is None


def test_missing_change_returns_none():
    provider = HttpJsonExternalMarketProvider(
        {"GOLD": HttpJsonSymbolConfig("https://x")},
        opener=_opener({"price": 2500, "timestamp": "t"}),
    )
    assert provider.fetch("GOLD") is None


def test_environment_configuration(monkeypatch):
    monkeypatch.setenv("EXTERNAL_US500_URL", "https://x")
    monkeypatch.setenv("EXTERNAL_US500_PRICE_PATH", "data.p")
    configs = HttpJsonExternalMarketProvider.from_environment_configs()
    assert configs["US500"].url == "https://x"
    assert configs["US500"].price_path == "data.p"


def test_timeout_must_be_positive():
    try:
        HttpJsonExternalMarketProvider({}, timeout=0)
        assert False
    except ValueError:
        assert True


def test_provider_contract_has_no_operational_signal_fields():
    provider = HttpJsonExternalMarketProvider(
        {"US10Y": HttpJsonSymbolConfig("https://x")},
        opener=_opener({"price": 4.2, "change": -0.03, "timestamp": "t"}),
    )
    result = provider.fetch("US10Y")
    assert set(result) == {"price", "change", "timestamp"}
    assert "buy" not in result
    assert "sell" not in result
