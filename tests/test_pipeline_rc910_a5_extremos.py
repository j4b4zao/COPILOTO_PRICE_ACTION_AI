from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from models.book_depth import BookDepthSnapshot, BookLevel


class StaticService:
    def __init__(self, snapshot):
        self.value = snapshot

    def snapshot(self, symbol):
        return self.value


def refresh(snapshot):
    pipeline = AnalysisPipeline(
        book_depth_service=StaticService(snapshot)
    )

    context = AnalysisContext()
    context.market.symbol = "WINZ26"

    pipeline.context = context
    pipeline._refresh_book_depth()

    return context.book_depth


def test_rc910_unavailable_remains_unavailable():
    original = BookDepthSnapshot.unavailable(
        symbol="WINZ26",
        source="PROVIDER_OFFLINE",
    )

    result = refresh(original)

    assert result.available is False
    assert result.symbol == "WINZ26"


def test_rc910_unavailable_preserves_source():
    original = BookDepthSnapshot.unavailable(
        symbol="WINZ26",
        source="PROVIDER_OFFLINE",
    )

    result = refresh(original)

    assert result.source == "PROVIDER_OFFLINE", (
        "RC910_UNAVAILABLE_SOURCE_CHANGED"
    )


def test_rc910_valid_snapshot_is_independent():
    original = BookDepthSnapshot.build(
        symbol="WINZ26",
        timestamp="2026-11-17T10:00:00",
        bids=[(100.0, 100.0)],
        asks=[(101.0, 20.0)],
        source="TEST",
    )

    result = refresh(original)

    assert result == original
    assert result is not original


def test_rc910_invalid_content_fails_closed():
    invalid = BookDepthSnapshot(
        symbol="WINZ26",
        timestamp="2026-11-17T10:00:00",
        bids=[BookLevel(100.0, 100.0)],
        asks=[BookLevel(99.0, 20.0)],
        source="INVALID_CROSSED_BOOK",
        available=True,
    )

    result = refresh(invalid)

    assert result.available is False
    assert result.source == "BOOK_DEPTH_INVALID_CONTENT"


def test_rc910_empty_available_snapshot_rejected():
    invalid = BookDepthSnapshot(
        symbol="WINZ26",
        timestamp="2026-11-17T10:00:00",
        bids=[],
        asks=[],
        source="INVALID_EMPTY_BOOK",
        available=True,
    )

    result = refresh(invalid)

    assert result.available is False
    assert result.source == "BOOK_DEPTH_INVALID_CONTENT"
