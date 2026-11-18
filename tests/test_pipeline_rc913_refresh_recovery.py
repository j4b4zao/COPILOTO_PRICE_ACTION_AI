import unittest

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext


class HostilePipeline(AnalysisPipeline):
    """Pipeline controlado para testar falhas antes das engines."""

    def __init__(self):
        super().__init__()
        self.failure_stage = None

    def _refresh_external_context(self):
        if self.failure_stage == "external":
            raise RuntimeError("RC913_EXTERNAL_FAILURE")

    def _refresh_book_depth(self):
        if self.failure_stage == "book":
            raise RuntimeError("RC913_BOOK_FAILURE")


class TestPipelineRC913RefreshRecovery(unittest.TestCase):

    @staticmethod
    def prepare_context():
        context = AnalysisContext()
        context.score.valid = True
        context.decision.valid = True
        context.alert.valid = True
        return context

    def assert_results_cleared(self, context):
        self.assertFalse(context.score.valid)
        self.assertFalse(context.decision.valid)
        self.assertFalse(context.alert.valid)

    def test_external_failure_clears_results(self):
        pipeline = HostilePipeline()
        pipeline.failure_stage = "external"
        context = self.prepare_context()

        with self.assertRaisesRegex(
            RuntimeError, "RC913_EXTERNAL_FAILURE"
        ):
            pipeline.executar(context)

        self.assert_results_cleared(context)

    def test_book_failure_clears_results(self):
        pipeline = HostilePipeline()
        pipeline.failure_stage = "book"
        context = self.prepare_context()

        with self.assertRaisesRegex(
            RuntimeError, "RC913_BOOK_FAILURE"
        ):
            pipeline.executar(context)

        self.assert_results_cleared(context)

    def test_external_failure_preserves_context_identity(self):
        pipeline = HostilePipeline()
        pipeline.failure_stage = "external"
        context = self.prepare_context()

        with self.assertRaises(RuntimeError):
            pipeline.executar(context)

        self.assertIs(pipeline.context, context)
        self.assert_results_cleared(context)

    def test_book_failure_preserves_context_identity(self):
        pipeline = HostilePipeline()
        pipeline.failure_stage = "book"
        context = self.prepare_context()

        with self.assertRaises(RuntimeError):
            pipeline.executar(context)

        self.assertIs(pipeline.context, context)
        self.assert_results_cleared(context)

    def test_repeated_failures_leave_no_residual_results(self):
        pipeline = HostilePipeline()

        for stage in ("external", "book", "external", "book"):
            with self.subTest(stage=stage):
                pipeline.failure_stage = stage
                context = self.prepare_context()

                with self.assertRaises(RuntimeError):
                    pipeline.executar(context)

                self.assert_results_cleared(context)

    def test_recovery_after_external_failure(self):
        pipeline = HostilePipeline()
        pipeline.failure_stage = "external"

        failed_context = self.prepare_context()

        with self.assertRaises(RuntimeError):
            pipeline.executar(failed_context)

        self.assert_results_cleared(failed_context)

        pipeline.failure_stage = None
        pipeline.engines = []

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
            setattr(
                pipeline,
                name,
                type("NoopRecorder", (), {"record": lambda self, ctx: None})()
            )

        pipeline._refresh_trader_psychology = lambda: None
        pipeline._publish_loop = lambda: None

        recovered_context = self.prepare_context()
        result = pipeline.executar(recovered_context)

        self.assertIs(result, recovered_context)
        self.assert_results_cleared(recovered_context)
        self.assert_results_cleared(failed_context)


if __name__ == "__main__":
    unittest.main()
