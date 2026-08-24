from types import SimpleNamespace

from core.analysis_context import AnalysisContext
from market.profitdll_bookdepth_runtime import ProfitDLLBookDepthRuntime


class Session:
    def __init__(self, payload=None):
        self.payload = payload
        self.status = SimpleNamespace(
            state="SUBSCRIBED", book_mode="LEGACY_PRICE_BOOK", symbol="WINV26",
            initialized=True, subscribed=True, callback_events=12,
        )
    def snapshot(self, symbol):
        return self.payload


def payload(bid=10, ask=9):
    return {
        "symbol": "WINV26", "timestamp": "2026-08-24T09:40:00",
        "bids": [
            {"price": 100.0, "quantity": bid, "orders": 2},
            {"price": 99.5, "quantity": 8, "orders": 1},
            {"price": 99.0, "quantity": 6, "orders": 1},
        ],
        "asks": [
            {"price": 100.5, "quantity": ask, "orders": 2},
            {"price": 101.0, "quantity": 7, "orders": 1},
            {"price": 101.5, "quantity": 5, "orders": 1},
        ],
    }


def test_runtime_requires_session():
    try:
        ProfitDLLBookDepthRuntime(None); assert False
    except ValueError:
        assert True


def test_poll_returns_available_snapshot():
    r = ProfitDLLBookDepthRuntime(Session(payload()))
    assert r.poll("WINV26").available is True


def test_poll_updates_source_report():
    r = ProfitDLLBookDepthRuntime(Session(payload()))
    r.poll("WINV26")
    assert r.last_source_report.total_snapshots == 1


def test_poll_updates_quality_report():
    r = ProfitDLLBookDepthRuntime(Session(payload()))
    r.poll("WINV26")
    assert r.last_quality_report.status in {"INITIALIZING", "VALID"}


def test_refresh_writes_context_book_depth():
    c = AnalysisContext(); c.market.symbol = "WINV26"
    r = ProfitDLLBookDepthRuntime(Session(payload()))
    snap = r.refresh(c)
    assert c.book_depth is snap and snap.available


def test_session_summary_records_samples():
    r = ProfitDLLBookDepthRuntime(Session(payload()))
    r.poll("WINV26")
    assert r.session_summary()["samples"] == 1


def test_render_contains_all_runtime_layers():
    r = ProfitDLLBookDepthRuntime(Session(payload())); r.poll("WINV26")
    text = r.render()
    assert "[PROFITDLL]" in text and "[BOOK SOURCE]" in text and "[BOOK QUALITY]" in text


def test_render_exposes_legacy_mode():
    r = ProfitDLLBookDepthRuntime(Session(payload())); r.poll("WINV26")
    assert "mode=LEGACY_PRICE_BOOK" in r.render()


def test_unavailable_book_is_recorded_fail_safe():
    r = ProfitDLLBookDepthRuntime(Session(None))
    snap = r.poll("WINV26")
    assert snap.available is False
    assert r.session_summary()["samples"] == 1


def test_runtime_does_not_modify_score():
    c = AnalysisContext(); c.market.symbol = "WINV26"
    r = ProfitDLLBookDepthRuntime(Session(payload())); r.refresh(c)
    assert c.score.total == 0.0
