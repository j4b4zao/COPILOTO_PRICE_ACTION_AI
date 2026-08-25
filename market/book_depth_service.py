"""Coleta e entrega fail-safe de profundidade real do Book."""

from __future__ import annotations

from models.book_depth import BookDepthProvider, BookDepthSnapshot


class BookDepthCollector:
    VERSION = "RC1-BOOK-DEPTH-COLLECTOR"

    def __init__(self, provider: BookDepthProvider, levels: int = 5):
        if not callable(getattr(provider, "snapshot", None)):
            raise TypeError("BookDepth provider deve expor snapshot(symbol).")
        self.provider = provider
        self.levels = max(1, int(levels))

    def collect(self, symbol: str) -> BookDepthSnapshot:
        symbol = str(symbol or "").upper().strip()
        if not symbol:
            return BookDepthSnapshot.unavailable(source="BOOK_SYMBOL_UNAVAILABLE")

        try:
            snapshot = self.provider.snapshot(symbol)
        except Exception:
            return BookDepthSnapshot.unavailable(
                symbol=symbol,
                source=self._source("PROVIDER_ERROR"),
            )

        if not isinstance(snapshot, BookDepthSnapshot):
            return BookDepthSnapshot.unavailable(
                symbol=symbol,
                source=self._source("INVALID_SNAPSHOT"),
            )

        if not snapshot.available:
            return snapshot

        if snapshot.symbol and snapshot.symbol.upper() != symbol:
            return BookDepthSnapshot.unavailable(
                symbol=symbol,
                source=self._source("SYMBOL_MISMATCH"),
            )

        return snapshot.top(self.levels)

    def _source(self, suffix: str) -> str:
        source = str(getattr(self.provider, "SOURCE", "UNKNOWN") or "UNKNOWN")
        return f"{source}:{suffix}"


class BookDepthService:
    """Ponte observacional entre provider de depth e AnalysisContext."""

    VERSION = "RC1-BOOK-DEPTH-SERVICE"

    def __init__(self, provider: BookDepthProvider, levels: int = 5):
        self.collector = BookDepthCollector(provider, levels=levels)

    def snapshot(self, symbol: str) -> BookDepthSnapshot:
        return self.collector.collect(symbol)

    def refresh(self, context) -> BookDepthSnapshot:
        market = getattr(context, "market", None)
        symbol = str(getattr(market, "symbol", "") or "")
        snapshot = self.snapshot(symbol)
        if not hasattr(context, "book_depth"):
            raise TypeError("AnalysisContext sem campo book_depth.")
        context.book_depth = snapshot
        return snapshot
