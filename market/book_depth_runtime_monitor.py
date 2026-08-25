"""Monitor runtime observacional para BookDepth real."""

from __future__ import annotations

from market_data.book_depth_quality_validator import BookDepthQualityValidator
from market_data.book_depth_session_recorder import BookDepthSessionRecorder
from market_data.book_depth_source_diagnostics import BookDepthSourceDiagnostics


class BookDepthRuntimeMonitor:
    VERSION = "RC1-BOOK-DEPTH-RUNTIME-MONITOR"

    def __init__(self, service, source_diagnostics=None, quality_validator=None, recorder=None):
        if not callable(getattr(service, "snapshot", None)):
            raise TypeError("BookDepth service deve expor snapshot(symbol).")
        self.service = service
        self.source_diagnostics = source_diagnostics or BookDepthSourceDiagnostics()
        self.quality_validator = quality_validator or BookDepthQualityValidator()
        self.recorder = recorder or BookDepthSessionRecorder()
        self.last_snapshot = None
        self.last_source_report = self.source_diagnostics.report
        self.last_quality_report = self.quality_validator.evaluate(None, self.last_source_report)

    def poll(self, symbol: str):
        snapshot = self.service.snapshot(symbol)
        self.last_snapshot = snapshot
        self.last_source_report = self.source_diagnostics.observe(snapshot)
        self.last_quality_report = self.quality_validator.evaluate(snapshot, self.last_source_report)
        self.recorder.record(self.last_source_report, self.last_quality_report)
        return snapshot

    def refresh(self, context):
        market = getattr(context, "market", None)
        symbol = str(getattr(market, "symbol", "") or "")
        snapshot = self.poll(symbol)
        if not hasattr(context, "book_depth"):
            raise TypeError("AnalysisContext sem campo book_depth.")
        context.book_depth = snapshot
        return snapshot

    def session_summary(self):
        return self.recorder.summary()

    def render(self) -> str:
        source = self.last_source_report
        quality = self.last_quality_report
        return (
            "[BOOK SOURCE] "
            f"status={source.status} symbol={source.symbol} fresh={source.fresh_snapshots} "
            f"duplicates={source.duplicate_snapshots} availability={source.availability_rate:.0%} "
            f"levels={source.bid_levels}/{source.ask_levels} spread={source.spread:.4f}\n"
            "[BOOK QUALITY] "
            f"status={quality.status} spread_ratio={quality.spread_ratio:.6f} "
            f"imbalance={quality.imbalance:.3f} concentration_edge={quality.concentration_edge:.3f} "
            f"anomalies={quality.anomaly_count} "
            f"reasons={','.join(quality.reasons) if quality.reasons else 'OK'}"
        )
