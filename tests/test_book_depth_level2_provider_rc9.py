from market_data.book_depth_level2_provider import BookDepthLevel2Reader, NormalizedLevel2BookDepthProvider


class Reader(BookDepthLevel2Reader):
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
    def read_book_depth(self, symbol):
        if self.error:
            raise self.error
        return self.payload


def payload():
    return {
        "symbol": "WINV26",
        "timestamp": "2026-08-23T10:00:00",
        "bids": [(100.0, 10, 2), (99.0, 20, 3)],
        "asks": [(101.0, 15, 2), (102.0, 25, 3)],
    }


def test_valid_payload_builds_snapshot():
    snap = NormalizedLevel2BookDepthProvider(Reader(payload()), source="PROFIT_LEVEL2").snapshot("WINV26")
    assert snap.available is True
    assert snap.source == "PROFIT_LEVEL2"


def test_provider_sorts_sides():
    p = payload(); p["bids"] = list(reversed(p["bids"])); p["asks"] = list(reversed(p["asks"]))
    snap = NormalizedLevel2BookDepthProvider(Reader(p)).snapshot("WINV26")
    assert snap.best_bid == 100.0 and snap.best_ask == 101.0


def test_limits_levels():
    p = payload(); p["bids"] += [(98, 1), (97, 1)]; p["asks"] += [(103, 1), (104, 1)]
    snap = NormalizedLevel2BookDepthProvider(Reader(p), max_levels=2).snapshot("WINV26")
    assert len(snap.bids) == 2 and len(snap.asks) == 2


def test_empty_symbol_is_unavailable():
    snap = NormalizedLevel2BookDepthProvider(Reader(payload())).snapshot("")
    assert snap.available is False


def test_reader_error_is_fail_safe():
    snap = NormalizedLevel2BookDepthProvider(Reader(error=RuntimeError("offline"))).snapshot("WINV26")
    assert snap.source.endswith("READER_ERROR")


def test_invalid_payload_is_unavailable():
    snap = NormalizedLevel2BookDepthProvider(Reader([])).snapshot("WINV26")
    assert snap.source.endswith("INVALID_PAYLOAD")


def test_symbol_mismatch_is_rejected():
    p = payload(); p["symbol"] = "WDOU26"
    snap = NormalizedLevel2BookDepthProvider(Reader(p)).snapshot("WINV26")
    assert snap.source.endswith("SYMBOL_MISMATCH")


def test_empty_side_is_rejected():
    p = payload(); p["asks"] = []
    snap = NormalizedLevel2BookDepthProvider(Reader(p)).snapshot("WINV26")
    assert snap.source.endswith("EMPTY_BOOK")


def test_invalid_level_is_rejected():
    p = payload(); p["bids"] = [(100, -1)]
    snap = NormalizedLevel2BookDepthProvider(Reader(p)).snapshot("WINV26")
    assert snap.available is False


def test_crossed_book_is_rejected():
    p = payload(); p["bids"] = [(102, 10)]; p["asks"] = [(101, 10)]
    snap = NormalizedLevel2BookDepthProvider(Reader(p)).snapshot("WINV26")
    assert snap.source.endswith("INVALID_BOOK")
