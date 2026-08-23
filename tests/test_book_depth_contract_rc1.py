import pytest

from models.book_depth import BookDepthProvider, BookDepthSnapshot, BookLevel


def test_book_level_validates_values():
    with pytest.raises(ValueError):
        BookLevel(price=0, quantity=1)
    with pytest.raises(ValueError):
        BookLevel(price=100, quantity=-1)


def test_build_snapshot_from_dicts_and_tuples():
    snap = BookDepthSnapshot.build(
        symbol="winv26",
        timestamp="2026-08-23T10:00:00",
        bids=[{"price": 100.0, "quantity": 20, "orders": 2}, (99.5, 10)],
        asks=[(100.5, 5), {"price": 101.0, "quantity": 15}],
        source="TEST",
    )
    assert snap.symbol == "WINV26"
    assert snap.available is True
    assert snap.best_bid == 100.0
    assert snap.best_ask == 100.5


def test_spread_and_quantities_are_derived():
    snap = BookDepthSnapshot.build(
        symbol="WIN",
        timestamp="t",
        bids=[(100, 30), (99, 20)],
        asks=[(101, 10), (102, 10)],
        source="TEST",
    )
    assert snap.spread == 1
    assert snap.bid_quantity == 50
    assert snap.ask_quantity == 20


def test_positive_imbalance_means_bid_dominant():
    snap = BookDepthSnapshot.build(
        symbol="WIN", timestamp="t", bids=[(100, 70)], asks=[(101, 30)], source="TEST"
    )
    assert snap.imbalance == 0.4
    assert snap.liquidity_pressure == "BID_DOMINANT"


def test_negative_imbalance_means_ask_dominant():
    snap = BookDepthSnapshot.build(
        symbol="WIN", timestamp="t", bids=[(100, 30)], asks=[(101, 70)], source="TEST"
    )
    assert snap.imbalance == -0.4
    assert snap.liquidity_pressure == "ASK_DOMINANT"


def test_balanced_book_is_neutral():
    snap = BookDepthSnapshot.build(
        symbol="WIN", timestamp="t", bids=[(100, 52)], asks=[(101, 48)], source="TEST"
    )
    assert snap.liquidity_pressure == "BALANCED"


def test_invalid_ordering_is_rejected():
    with pytest.raises(ValueError):
        BookDepthSnapshot.build(
            symbol="WIN", timestamp="t", bids=[(99, 1), (100, 1)], asks=[(101, 1)], source="TEST"
        )
    with pytest.raises(ValueError):
        BookDepthSnapshot.build(
            symbol="WIN", timestamp="t", bids=[(100, 1)], asks=[(102, 1), (101, 1)], source="TEST"
        )


def test_crossed_book_is_rejected():
    with pytest.raises(ValueError):
        BookDepthSnapshot.build(
            symbol="WIN", timestamp="t", bids=[(101, 1)], asks=[(101, 1)], source="TEST"
        )


def test_top_preserves_readonly_contract():
    snap = BookDepthSnapshot.build(
        symbol="WIN",
        timestamp="t",
        bids=[(100, 10), (99, 9), (98, 8)],
        asks=[(101, 10), (102, 9), (103, 8)],
        source="TEST",
    )
    top = snap.top(2)
    assert len(top.bids) == 2
    assert len(top.asks) == 2
    with pytest.raises(Exception):
        top.symbol = "OTHER"


def test_unavailable_and_provider_contract():
    snap = BookDepthSnapshot.unavailable("WIN", "NO_SOURCE")
    assert snap.available is False
    assert snap.liquidity_pressure == "BALANCED"
    assert snap.to_dict()["source"] == "NO_SOURCE"
    with pytest.raises(NotImplementedError):
        BookDepthProvider().snapshot("WIN")
