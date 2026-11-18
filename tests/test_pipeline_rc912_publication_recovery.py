import unittest
from dataclasses import fields

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext


PRESERVED = {
    "market",
    "multi_timeframe",
    "external_market",
    "economic_calendar",
    "book_depth",
    "order_flow_state",
    "narrative",
}


class ControlledEngine:
    ENABLED = True
    PRIORITY = 1

    def executar(self, context):
        context.score.valid = True
        context.decision.valid = True
        context.alert.valid = True


class NeutralRecorder:
    def record(self, context):
        return None


class ControlledPipeline(AnalysisPipeline):

    def __init__(self):
        super().__init__()
        self.fail_publication = False
        self.publication_calls = 0

    def _publish_loop(self):
        self.publication_calls += 1

        if self.fail_publication:
            raise RuntimeError("RC912_PUBLISH_FAILURE")


def prepare_pipeline():
    pipeline = ControlledPipeline()
    pipeline.engines = [ControlledEngine()]

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
        setattr(pipeline, name, NeutralRecorder())

    return pipeline


def residuals(context):
    reference = AnalysisContext()

    return [
        field.name
        for field in fields(context)
        if field.name not in PRESERVED
        and getattr(context, field.name)
        != getattr(reference, field.name)
    ]


class TestPipelineRC912PublicationRecovery(unittest.TestCase):

    def test_publication_failure_propagates(self):
        pipeline = prepare_pipeline()
        pipeline.fail_publication = True

        with self.assertRaisesRegex(
            RuntimeError,
            "RC912_PUBLISH_FAILURE",
        ):
            pipeline.executar(AnalysisContext())

    def test_publication_failure_clears_results(self):
        pipeline = prepare_pipeline()
        pipeline.fail_publication = True
        context = AnalysisContext()

        with self.assertRaises(RuntimeError):
            pipeline.executar(context)

        self.assertEqual(residuals(context), [])

    def test_success_preserves_results(self):
        pipeline = prepare_pipeline()
        context = AnalysisContext()

        result = pipeline.executar(context)

        self.assertIs(result, context)
        self.assertTrue(context.score.valid)
        self.assertTrue(context.decision.valid)
        self.assertTrue(context.alert.valid)

    def test_recovery_after_failure(self):
        pipeline = prepare_pipeline()
        pipeline.fail_publication = True
        context = AnalysisContext()

        with self.assertRaises(RuntimeError):
            pipeline.executar(context)

        self.assertEqual(residuals(context), [])

        pipeline.fail_publication = False
        pipeline.executar(context)

        self.assertTrue(context.score.valid)
        self.assertTrue(context.decision.valid)
        self.assertTrue(context.alert.valid)

    def test_repeated_failures_do_not_accumulate_results(self):
        pipeline = prepare_pipeline()
        pipeline.fail_publication = True
        context = AnalysisContext()

        for _ in range(3):
            with self.assertRaises(RuntimeError):
                pipeline.executar(context)

            self.assertEqual(residuals(context), [])

        self.assertEqual(pipeline.publication_calls, 3)


if __name__ == "__main__":
    unittest.main()
