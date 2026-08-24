from types import SimpleNamespace

from market_data.profitdll_book_depth_bridge import (
    ProfitDLLBookDepthBridge,
    ProfitDLLSessionLevel2Reader,
)


class Session:
    def __init__(self, payload=None, initialized=True, subscribed=True, symbol="WINV26"):
        self.payload = payload
        self.status = SimpleNamespace(initialized=initialized, subscribed=subscribed, symbol=symbol)
    def snapshot(self, symbol):
        return self.payload


def payload():
    return {
        "symbol": "WINV26",
        "timestamp": "2026-08-24T09:30:00",
        "bids": [
            {"price": 100.0, "quantity": 10, "orders": 2},
            {"price": 99.5, "quantity": 8, "orders": 1},
            {"price": 99.0, "quantity": 6, "orders": 1},
        ],
        "asks": [
            {"price": 100.5, "quantity": 9, "orders": 2},
            {"price": 101.0, "quantity": 7, "orders": 1},
            {"price": 101.5, "quantity": 5, "orders": 1},
        ],
        "source": "PROFITDLL_LEGACY_PRICE_BOOK",
    }


def test_reader_requires_session_contract():
    try:
        ProfitDLLSessionLevel2Reader(object())
        assert False
    except TypeError:
        assert True


def test_reader_rejects_uninitialized_session():
    r = ProfitDLLSessionLevel2Reader(Session(payload(), initialized=False))
    try:
        r.read_book_depth("WINV26"); assert False
    except RuntimeError: assert True


def test_reader_rejects_unsubscribed_session():
    r = ProfitDLLSessionLevel2Reader(Session(payload(), subscribed=False))
    try:
        r.read_book_depth("WINV26"); assert False
    except RuntimeError: assert True


def test_reader_rejects_symbol_mismatch():
    r = ProfitDLLSessionLevel2Reader(Session(payload(), symbol="WDOU26"))
    try:
        r.read_book_depth("WINV26"); assert False
    except RuntimeError: assert True


def test_reader_requires_payload_dict():
    r = ProfitDLLSessionLevel2Reader(Session(None))
    try:
        r.read_book_depth("WINV26"); assert False
    except RuntimeError: assert True


def test_bridge_builds_available_snapshot():
    bridge = ProfitDLLBookDepthBridge(Session(payload()))
    snap = bridge.snapshot("WINV26")
    assert snap.available is True
    assert snap.symbol == "WINV26"


def test_bridge_preserves_order_counts_and_quantities():
    bridge = ProfitDLLBookDepthBridge(Session(payload()))
    snap = bridge.snapshot("WINV26")
    assert snap.bids[0].orders == 2
    assert snap.bids[0].quantity == 10


def test_bridge_uses_profitdll_source():
    bridge = ProfitDLLBookDepthBridge(Session(payload()))
    snap = bridge.snapshot("WINV26")
    assert snap.source == "PROFITDLL"


def test_bridge_respects_level_limit():
    bridge = ProfitDLLBookDepthBridge(Session(payload()), levels=2)
    snap = bridge.snapshot("WINV26")
    assert len(snap.bids) == 2 and len(snap.asks) == 2


def test_bridge_unavailable_when_session_has_no_book():
    bridge = ProfitDLLBookDepthBridge(Session(None))
    snap = bridge.snapshot("WINV26")
    assert snap.available is False
