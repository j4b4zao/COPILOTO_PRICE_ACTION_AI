from types import SimpleNamespace

from market_data.book_depth_quality_validator import BookDepthQualityValidator
from models.book_depth import BookDepthSnapshot


def source(status="READY", duplicate_rate=0.0, availability_rate=1.0):
    return SimpleNamespace(status=status, duplicate_rate=duplicate_rate, availability_rate=availability_rate)


def snap(bids=None, asks=None):
    return BookDepthSnapshot.build(
        symbol="WINV26", timestamp="2026-08-23T10:00:00",
        bids=bids or [(100.0, 30), (99.5, 20), (99.0, 10)],
        asks=asks or [(100.5, 25), (101.0, 15), (101.5, 10)], source="TEST")


def test_no_data():
    r = BookDepthQualityValidator().evaluate(None, source("NO_DATA", 0, 0))
    assert r.status == "NO_DATA"


def test_unavailable_snapshot():
    r = BookDepthQualityValidator().evaluate(BookDepthSnapshot.unavailable("WIN"), source("UNAVAILABLE", 0, 0))
    assert r.status == "UNAVAILABLE"


def test_valid_book():
    r = BookDepthQualityValidator().evaluate(snap(), source())
    assert r.status == "VALID"


def test_shallow_book():
    r = BookDepthQualityValidator().evaluate(snap(bids=[(100, 10)], asks=[(101, 10)]), source())
    assert r.status == "SHALLOW"


def test_wide_spread_is_degraded():
    r = BookDepthQualityValidator().evaluate(snap(bids=[(100,10),(99,9),(98,8)], asks=[(120,10),(121,9),(122,8)]), source())
    assert r.status == "DEGRADED"
    assert "WIDE_SPREAD" in r.reasons


def test_duplicate_rate_is_degraded():
    r = BookDepthQualityValidator().evaluate(snap(), source(duplicate_rate=0.9))
    assert r.status == "DEGRADED"


def test_low_availability_is_degraded():
    r = BookDepthQualityValidator().evaluate(snap(), source(availability_rate=0.5))
    assert r.status == "DEGRADED"


def test_source_degraded_propagates():
    r = BookDepthQualityValidator().evaluate(snap(), source(status="DEGRADED"))
    assert r.status == "DEGRADED"


def test_concentration_metrics_are_exposed():
    r = BookDepthQualityValidator().evaluate(snap(
        bids=[(100,50),(99.5,30),(99,20),(98.5,100)],
        asks=[(100.5,20),(101,20),(101.5,10),(102,50)]), source())
    assert 0 <= r.top_bid_concentration <= 1
    assert 0 <= r.top_ask_concentration <= 1
    assert r.concentration_edge >= 0


def test_passive_only():
    assert BookDepthQualityValidator().evaluate(snap(), source()).passive_only is True
