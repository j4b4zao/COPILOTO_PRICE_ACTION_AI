import unittest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from external_context.external_market_state import ExternalMarketState
from models.book_depth import BookDepthSnapshot


class NoopRecorder:
    def record(self, context):
        pass


class ExternalService:
    def __init__(self):
        self.calls = 0

    def snapshot(self):
        self.calls += 1
        return ExternalMarketState(
            valid=True,
            timestamp="2026-11-18T13:00:00",
            us500=6000.0,
            nasdaq=21000.0,
            dxy=100.0,
            risk_on_off="RISK_ON",
            global_bias="BULLISH",
            confidence=0.9,
        )


class BookService:
    def __init__(self):
        self.calls = 0

    def snapshot(self, symbol):
        self.calls += 1
        return BookDepthSnapshot.build(
            symbol=symbol or "WINZ26",
            timestamp="2026-11-18T13:00:00",
            bids=[(180000.0, 100, 10)],
            asks=[(180005.0, 120, 12)],
            source="RC914_CONTROLLED",
        )


class DiagnosticPipeline(AnalysisPipeline):
    def __init__(self, external_service, book_service):
        super().__init__(
            external_context_service=external_service,
            book_depth_service=book_service,
        )

        self.engines = []

        for name in (
            "book_diagnostics_replay",
            "score_regime_mtf_ab",
            "score_external_context_ab",
            "score_order_flow_ab",
            "score_order_flow_structure_ab",
            "score_book_depth_ab",
            "score_microstructure_eligibility_ab",
            "microstructure_confluence_replay",
            "microstructure_eligibility_replay",
        ):
            setattr(self, name, NoopRecorder())

    def _refresh_trader_psychology(self):
        pass


class TestRC914StaleState(unittest.TestCase):

    def setUp(self):
        self.external = ExternalService()
        self.book = BookService()
        self.pipeline = DiagnosticPipeline(
            self.external,
            self.book,
        )
        self.context = AnalysisContext()

    def test_01_active_services_produce_valid_states(self):
        self.pipeline.executar(self.context)

        self.assertTrue(self.context.external_market.valid)
        self.assertTrue(self.context.book_depth.available)

    def test_02_external_removed_invalidates_previous_state(self):
        self.pipeline.executar(self.context)

        self.pipeline.external_context_service = None
        self.pipeline.executar(self.context)

        self.assertFalse(self.context.external_market.valid)
        self.assertEqual(self.context.external_market.timestamp, "")
        self.assertIn(
            "EXTERNAL_CONTEXT_SERVICE_UNAVAILABLE",
            self.context.external_market.reasons,
        )

    def test_03_book_removed_invalidates_previous_state(self):
        self.pipeline.executar(self.context)

        self.pipeline.book_depth_service = None
        self.pipeline.executar(self.context)

        self.assertFalse(self.context.book_depth.available)
        self.assertEqual(self.context.book_depth.timestamp, "")
        self.assertEqual(
            self.context.book_depth.source,
            "BOOK_DEPTH_SERVICE_UNAVAILABLE",
        )

    def test_04_both_services_removed(self):
        self.pipeline.executar(self.context)

        self.pipeline.external_context_service = None
        self.pipeline.book_depth_service = None

        self.pipeline.executar(self.context)

        self.assertFalse(self.context.external_market.valid)
        self.assertFalse(self.context.book_depth.available)

    def test_05_services_recovered(self):
        self.pipeline.executar(self.context)

        self.pipeline.external_context_service = None
        self.pipeline.book_depth_service = None

        self.pipeline.executar(self.context)

        self.pipeline.external_context_service = self.external
        self.pipeline.book_depth_service = self.book

        self.pipeline.executar(self.context)

        self.assertTrue(self.context.external_market.valid)
        self.assertTrue(self.context.book_depth.available)

    def test_06_different_contexts_remain_independent(self):
        context_a = AnalysisContext()
        context_b = AnalysisContext()

        self.pipeline.executar(context_a)

        self.pipeline.external_context_service = None
        self.pipeline.book_depth_service = None

        self.pipeline.executar(context_b)

        self.assertTrue(context_a.external_market.valid)
        self.assertTrue(context_a.book_depth.available)

        self.assertFalse(context_b.external_market.valid)
        self.assertFalse(context_b.book_depth.available)

    def test_07_repeated_unavailable_cycles(self):
        self.pipeline.external_context_service = None
        self.pipeline.book_depth_service = None

        for _ in range(5):
            self.pipeline.executar(self.context)

            self.assertFalse(self.context.external_market.valid)
            self.assertFalse(self.context.book_depth.available)

            self.assertEqual(
                self.context.external_market.reasons,
                ["EXTERNAL_CONTEXT_SERVICE_UNAVAILABLE"],
            )

    def test_08_snapshot_services_called_only_when_active(self):
        self.pipeline.executar(self.context)

        self.assertEqual(self.external.calls, 1)
        self.assertEqual(self.book.calls, 1)

        self.pipeline.external_context_service = None
        self.pipeline.book_depth_service = None

        self.pipeline.executar(self.context)

        self.assertEqual(self.external.calls, 1)
        self.assertEqual(self.book.calls, 1)


if __name__ == "__main__":
    unittest.main()
