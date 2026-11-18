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


def differences(context, reference):
    return [
        field.name
        for field in fields(context)
        if field.name not in PRESERVED
        and getattr(context, field.name)
        != getattr(reference, field.name)
    ]


class HostileEngine:
    ENABLED = True
    PRIORITY = 1

    def executar(self, context):
        for name in (
            "score",
            "decision",
            "risk",
            "alert",
            "strategy",
        ):
            getattr(context, name).valid = True

        raise RuntimeError("RC911_ENGINE_FAILURE")


class RecoveryEngine:
    ENABLED = True
    PRIORITY = 1

    def __init__(self):
        self.calls = 0

    def executar(self, context):
        self.calls += 1

        if self.calls == 1:
            context.score.valid = True
            context.decision.valid = True
            raise RuntimeError("RC911_FIRST_FAILURE")

        if context.score.valid or context.decision.valid:
            raise AssertionError("RC911_RESIDUAL_STATE")

        context.score.valid = True


class NeutralRecorder:
    def record(self, context):
        return None


def neutralize_recorders(pipeline):
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


class PipelineRC911RecoveryTests(unittest.TestCase):

    def test_engine_failure_clears_results(self):
        pipeline = AnalysisPipeline()
        pipeline.engines = [HostileEngine()]

        context = AnalysisContext()

        with self.assertRaisesRegex(
            RuntimeError,
            "RC911_ENGINE_FAILURE",
        ):
            pipeline.executar(context)

        self.assertEqual(
            differences(context, AnalysisContext()),
            [],
        )

    def test_recovery_between_cycles(self):
        engine = RecoveryEngine()

        pipeline = AnalysisPipeline()
        pipeline.engines = [engine]
        neutralize_recorders(pipeline)

        context = AnalysisContext()

        with self.assertRaisesRegex(
            RuntimeError,
            "RC911_FIRST_FAILURE",
        ):
            pipeline.executar(context)

        self.assertEqual(
            differences(context, AnalysisContext()),
            [],
        )

        pipeline.executar(context)
        pipeline.executar(context)

        self.assertEqual(engine.calls, 3)
        self.assertTrue(context.score.valid)

    def test_preserves_market_states(self):
        context = AnalysisContext()

        market = context.market
        external = context.external_market
        book = context.book_depth

        context.clear_results()

        self.assertIs(context.market, market)
        self.assertIs(context.external_market, external)
        self.assertIs(context.book_depth, book)

    def test_clears_mutable_collections(self):
        context = AnalysisContext()

        count = 0

        for field in fields(context):
            if field.name in PRESERVED:
                continue

            obj = getattr(context, field.name)

            if not hasattr(obj, "__dataclass_fields__"):
                continue

            for inner in fields(obj):
                value = getattr(obj, inner.name)

                if isinstance(value, list):
                    value.append("RC911_MARKER")
                    count += 1

                elif isinstance(value, dict):
                    value["RC911_MARKER"] = True
                    count += 1

                elif isinstance(value, set):
                    value.add("RC911_MARKER")
                    count += 1

        self.assertGreater(count, 0)

        context.clear_results()

        self.assertEqual(
            differences(context, AnalysisContext()),
            [],
        )

    def test_repeated_cleanup(self):
        context = AnalysisContext()

        for _ in range(20):
            context.clear_results()

            self.assertEqual(
                differences(context, AnalysisContext()),
                [],
            )


if __name__ == "__main__":
    unittest.main()
