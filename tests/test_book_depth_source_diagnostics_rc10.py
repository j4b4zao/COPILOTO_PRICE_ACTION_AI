from models.book_depth import BookDepthSnapshot
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics


def snap(symbol="WINV26", shift=0, levels=3):
    bids = [(100-shift-i, 100-i*10, 2) for i in range(levels)]
    asks = [(101+shift+i, 90-i*10, 2) for i in range(levels)]
    return BookDepthSnapshot.build(symbol=symbol, timestamp=f"t{shift}", bids=bids, asks=asks, source="TEST")


def test_no_data_status():
    d = BookDepthSourceDiagnostics()
    assert d.report.status == "NO_DATA"


def test_unavailable_status():
    d = BookDepthSourceDiagnostics()
    d.observe(BookDepthSnapshot.unavailable("WINV26", "TEST"))
    assert d.report.status == "UNAVAILABLE"


def test_initializing_before_three_fresh_snapshots():
    d = BookDepthSourceDiagnostics()
    d.observe(snap(shift=0)); d.observe(snap(shift=1))
    assert d.report.status == "INITIALIZING"


def test_ready_after_three_fresh_snapshots():
    d = BookDepthSourceDiagnostics()
    for i in range(3): d.observe(snap(shift=i))
    assert d.report.status == "READY"


def test_shallow_when_fewer_than_three_levels_per_side():
    d = BookDepthSourceDiagnostics()
    d.observe(snap(levels=2))
    assert d.report.status == "SHALLOW"


def test_duplicate_is_counted():
    d = BookDepthSourceDiagnostics(); s = snap()
    d.observe(s); d.observe(s)
    assert d.report.duplicate_snapshots == 1


def test_excessive_duplicates_degrade_source():
    d = BookDepthSourceDiagnostics(); s = snap()
    d.observe(s)
    for _ in range(4): d.observe(s)
    assert d.report.status == "DEGRADED"


def test_symbol_change_is_counted():
    d = BookDepthSourceDiagnostics()
    d.observe(snap("WINV26")); d.observe(snap("WDOU26", shift=1))
    assert d.report.symbol_changes == 1


def test_report_exposes_spread_and_imbalance():
    d = BookDepthSourceDiagnostics(); d.observe(snap())
    assert d.report.spread > 0
    assert -1.0 <= d.report.imbalance <= 1.0


def test_clear_resets_counters():
    d = BookDepthSourceDiagnostics(); d.observe(snap()); d.clear()
    assert d.report.total_snapshots == 0
    assert d.report.status == "NO_DATA"
