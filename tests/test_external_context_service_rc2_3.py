import pytest

from external_context.external_context_service import ExternalContextService
from external_context.external_market_state import ExternalMarketState


class Provider:
    def __init__(self, changes):
        self.changes = changes

    def fetch(self, symbol):
        price = {
            "US500": 6000.0,
            "NASDAQ": 21000.0,
            "DXY": 98.0,
            "VIX": 14.0,
            "US10Y": 4.2,
            "OIL": 72.0,
            "GOLD": 2500.0,
        }[symbol]
        return {
            "price": price,
            "change": self.changes.get(symbol, 0.0),
            "timestamp": "2026-08-23T14:00:00-04:00",
        }


class CollectorStub:
    def __init__(self, state):
        self.state = state

    def collect(self):
        return self.state


def test_risk_on_pipeline():
    provider = Provider({"US500": 1, "NASDAQ": 1, "DXY": -1, "VIX": -1})
    state = ExternalContextService(provider=provider).snapshot()
    assert state.valid is True
    assert state.risk_on_off == "RISK_ON"
    assert state.global_bias == "BULLISH"
    assert state.confidence == 1.0


def test_risk_off_pipeline():
    provider = Provider({"US500": -1, "NASDAQ": -1, "DXY": 1, "VIX": 1})
    state = ExternalContextService(provider=provider).snapshot()
    assert state.risk_on_off == "RISK_OFF"
    assert state.global_bias == "BEARISH"


def test_neutral_pipeline():
    provider = Provider({"US500": 1, "NASDAQ": -1, "DXY": -1, "VIX": 1})
    state = ExternalContextService(provider=provider).snapshot()
    assert state.risk_on_off == "NEUTRAL"
    assert state.global_bias == "NEUTRAL"


def test_optional_markets_do_not_block_context():
    class EssentialOnlyProvider(Provider):
        def fetch(self, symbol):
            if symbol in {"US10Y", "OIL", "GOLD"}:
                return None
            return super().fetch(symbol)

    provider = EssentialOnlyProvider({"US500": 1, "NASDAQ": 1, "DXY": -1, "VIX": -1})
    state = ExternalContextService(provider=provider).snapshot()
    assert state.valid is True
    assert state.risk_on_off == "RISK_ON"


def test_missing_essential_market_returns_invalid_neutral_state():
    class MissingProvider(Provider):
        def fetch(self, symbol):
            if symbol == "VIX":
                return None
            return super().fetch(symbol)

    provider = MissingProvider({"US500": 1, "NASDAQ": 1, "DXY": -1})
    state = ExternalContextService(provider=provider).snapshot()
    assert state.valid is False
    assert state.risk_on_off == "NEUTRAL"
    assert state.confidence == 0.0


def test_interpret_accepts_precollected_state():
    state = ExternalMarketState(valid=True, us500_change=1, nasdaq_change=1, dxy_change=-1, vix_change=-1)
    result = ExternalContextService(collector=CollectorStub(state)).interpret(state)
    assert result.risk_on_off == "RISK_ON"


def test_provider_and_collector_are_mutually_exclusive():
    with pytest.raises(ValueError):
        ExternalContextService(provider=Provider({}), collector=CollectorStub(ExternalMarketState()))


def test_invalid_collector_contract_is_rejected():
    with pytest.raises(TypeError):
        ExternalContextService(collector=object())


def test_collector_must_return_external_market_state():
    service = ExternalContextService(collector=CollectorStub({"invalid": True}))
    with pytest.raises(TypeError):
        service.snapshot()


def test_service_has_no_operational_order_api():
    service = ExternalContextService(provider=Provider({}))
    assert not hasattr(service, "buy")
    assert not hasattr(service, "sell")
    assert not hasattr(service, "execute_order")
