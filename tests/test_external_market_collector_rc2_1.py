from external_context.external_market_collector import ExternalMarketCollector


class FakeProvider:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def fetch(self, symbol):
        self.calls.append(symbol)
        return self.payloads.get(symbol)


def _base_payloads():
    return {
        "US500": {"price": 6500, "change": 0.4, "timestamp": "2026-08-23T13:59:00-04:00"},
        "NASDAQ": {"price": 23500, "change": 0.6, "timestamp": "2026-08-23T14:00:00-04:00"},
        "DXY": {"price": 98.2, "change": -0.2, "timestamp": "2026-08-23T14:00:00-04:00"},
        "VIX": {"price": 15.4, "change": -0.5, "timestamp": "2026-08-23T13:58:00-04:00"},
        "US10Y": {"price": 4.1, "change": 0.02},
        "OIL": {"price": 76.5, "change": 0.3},
        "GOLD": {"price": 2500, "change": -0.1},
    }


def test_provider_is_optional_for_legacy_dict_collection():
    collector = ExternalMarketCollector()
    assert collector.provider is None


def test_invalid_provider_is_rejected():
    try:
        ExternalMarketCollector(object())
        assert False
    except TypeError:
        assert True


def test_collect_requires_configured_provider():
    collector = ExternalMarketCollector()
    try:
        collector.collect()
        assert False
    except RuntimeError:
        assert True


def test_provider_collection_populates_all_markets():
    provider = FakeProvider(_base_payloads())
    state = ExternalMarketCollector(provider).collect()
    assert state.valid is True
    assert state.us500 == 6500
    assert state.nasdaq_change == 0.6
    assert state.oil == 76.5


def test_provider_uses_latest_available_timestamp():
    state = ExternalMarketCollector(FakeProvider(_base_payloads())).collect()
    assert state.timestamp == "2026-08-23T14:00:00-04:00"


def test_optional_markets_can_be_missing_in_provider_mode():
    payloads = _base_payloads()
    payloads.pop("US10Y")
    payloads.pop("OIL")
    payloads.pop("GOLD")
    state = ExternalMarketCollector(FakeProvider(payloads)).collect()
    assert state.valid is True
    assert state.us10y == 0.0


def test_core_context_market_missing_invalidates_provider_snapshot():
    payloads = _base_payloads()
    payloads.pop("DXY")
    state = ExternalMarketCollector(FakeProvider(payloads)).collect()
    assert state.valid is False
    assert any("DXY" in reason for reason in state.reasons)


def test_invalid_provider_payload_is_treated_as_missing():
    payloads = _base_payloads()
    payloads["VIX"] = {"price": "bad", "change": 1.0}
    state = ExternalMarketCollector(FakeProvider(payloads)).collect()
    assert state.valid is False


def test_legacy_collection_still_requires_all_markets_by_default():
    data = {
        "us500": 6500,
        "nasdaq": 23500,
        "dxy": 98.2,
        "vix": 15.4,
        "us10y": 4.1,
        "oil": 76.5,
        "gold": 2500,
    }
    state = ExternalMarketCollector().coletar(data)
    assert state.valid is True


def test_collector_never_creates_operational_direction_fields():
    state = ExternalMarketCollector(FakeProvider(_base_payloads())).collect()
    assert not hasattr(state, "signal")
    assert not hasattr(state, "action")
    assert state.global_bias == "NEUTRAL"
