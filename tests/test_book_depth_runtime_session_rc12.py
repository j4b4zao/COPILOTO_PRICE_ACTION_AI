from types import SimpleNamespace

from core.analysis_context import AnalysisContext
from market.book_depth_runtime_monitor import BookDepthRuntimeMonitor
from market_data.book_depth_session_recorder import BookDepthSessionRecorder
from models.book_depth import BookDepthSnapshot


class Service:
    def __init__(self, snapshots):
        self.snapshots = iter(snapshots)
    def snapshot(self, symbol):
        return next(self.snapshots)


def snap(symbol="WINV26", bid=120, ask=80):
    return BookDepthSnapshot.build(
        symbol=symbol,
        timestamp="2026-08-23T10:00:00",
        bids=[(100.0, bid, 3), (99.5, 80, 2), (99.0, 50, 1)],
        asks=[(100.5, ask, 2), (101.0, 50, 1), (101.5, 30, 1)],
        source="TEST",
    )


def test_monitor_initial_state():
    m = BookDepthRuntimeMonitor(Service([snap()]))
    assert m.last_source_report.status == "NO_DATA"


def test_poll_records_snapshot():
    m = BookDepthRuntimeMonitor(Service([snap()]))
    result = m.poll("WINV26")
    assert result.available is True
    assert m.recorder.size == 1


def test_refresh_writes_context():
    c = AnalysisContext(); c.market.symbol = "WINV26"
    m = BookDepthRuntimeMonitor(Service([snap()]))
    result = m.refresh(c)
    assert c.book_depth is result


def test_duplicate_snapshot_is_tracked():
    s = snap(); m = BookDepthRuntimeMonitor(Service([s, s]))
    m.poll("WINV26"); m.poll("WINV26")
    assert m.last_source_report.duplicate_snapshots == 1


def test_session_summary_exposes_valid_rate():
    s1, s2, s3 = snap(), snap(bid=130), snap(bid=140)
    m = BookDepthRuntimeMonitor(Service([s1, s2, s3]))
    m.poll("WINV26"); m.poll("WINV26"); m.poll("WINV26")
    assert "valid_rate" in m.session_summary()


def test_render_contains_source_and_quality():
    m = BookDepthRuntimeMonitor(Service([snap()])); m.poll("WINV26")
    text = m.render()
    assert "[BOOK SOURCE]" in text and "[BOOK QUALITY]" in text


def test_recorder_retention():
    r = BookDepthSessionRecorder(max_samples=2)
    source = SimpleNamespace(status="READY", duplicate_rate=0.0, availability_rate=1.0, symbol="WINV26")
    quality = SimpleNamespace(status="VALID", levels_bid=3, levels_ask=3, spread=0.5, spread_ratio=0.000005,
                              imbalance=0.2, top_bid_concentration=0.7, top_ask_concentration=0.6,
                              concentration_edge=0.1, anomaly_count=0)
    r.record(source, quality); r.record(source, quality); r.record(source, quality)
    assert r.size == 2


def test_recorder_clear():
    r = BookDepthSessionRecorder()
    source = SimpleNamespace(status="READY", duplicate_rate=0.0, availability_rate=1.0, symbol="WINV26")
    quality = SimpleNamespace(status="VALID", levels_bid=3, levels_ask=3, spread=0.5, spread_ratio=0.0,
                              imbalance=0.0, top_bid_concentration=0.5, top_ask_concentration=0.5,
                              concentration_edge=0.0, anomaly_count=0)
    r.record(source, quality); r.clear()
    assert r.size == 0


def test_summary_counts_anomalies():
    r = BookDepthSessionRecorder()
    source = SimpleNamespace(status="DEGRADED", duplicate_rate=0.9, availability_rate=1.0, symbol="WINV26")
    quality = SimpleNamespace(status="DEGRADED", levels_bid=3, levels_ask=3, spread=20.0, spread_ratio=0.01,
                              imbalance=0.0, top_bid_concentration=0.5, top_ask_concentration=0.5,
                              concentration_edge=0.0, anomaly_count=2)
    r.record(source, quality)
    assert r.summary()["total_anomalies"] == 2


def test_runtime_monitor_does_not_touch_score():
    c = AnalysisContext(); c.market.symbol = "WINV26"
    m = BookDepthRuntimeMonitor(Service([snap()])); m.refresh(c)
    assert c.score.total == 0.0
