import math
import unittest

from analysis.research.book_methodology_observer import (
    BookMethodologyObserver,
    DecisionProcessObservation,
)


class BookMethodologyObserverTests(unittest.TestCase):
    def test_complete_process_is_observational(self):
        result = BookMethodologyObserver.audit_decision_process(
            DecisionProcessObservation(True, True, True, True, False, True)
        )
        self.assertEqual(result.status, "PROCESS_COMPLETE")
        self.assertEqual(result.process_completion_rate, 1.0)
        self.assertTrue(result.observational_only)
        self.assertFalse(result.score_influence_allowed)
        self.assertFalse(result.risk_influence_allowed)
        self.assertFalse(result.decision_influence_allowed)
        self.assertFalse(result.order_execution_allowed)

    def test_gaps_and_rule_violations_are_reported_without_blocking(self):
        result = BookMethodologyObserver.audit_decision_process(
            DecisionProcessObservation(
                False, True, False, False, True, False,
                ("CHASED_ENTRY", "CHASED_ENTRY", "MOVED_STOP"),
            )
        )
        self.assertEqual(result.status, "PROCESS_GAPS_OBSERVED")
        self.assertEqual(result.process_completion_rate, 1 / 6)
        self.assertEqual(result.rule_violation_codes, ("CHASED_ENTRY", "MOVED_STOP"))
        self.assertIn("DISCONFIRMING_EVIDENCE_MISSING", result.evidence_codes)

    def test_r_multiple_report_calculates_expectancy_and_drawdown(self):
        result = BookMethodologyObserver.analyze_r_multiples(
            (1.0, -1.0, 2.0, -0.5, 0.0), opportunities=10, minimum_sample=5
        )
        self.assertTrue(result.sample_sufficient)
        self.assertAlmostEqual(result.expectancy_r, 0.3)
        self.assertAlmostEqual(result.total_r, 1.5)
        self.assertAlmostEqual(result.maximum_drawdown_r, 1.0)
        self.assertAlmostEqual(result.opportunity_adjusted_expectancy_r, 0.15)
        self.assertAlmostEqual(result.win_rate, 0.4)
        self.assertAlmostEqual(result.loss_rate, 0.4)

    def test_empty_and_small_samples_remain_diagnostic(self):
        result = BookMethodologyObserver.analyze_r_multiples(())
        self.assertIsNone(result.expectancy_r)
        self.assertIn("INSUFFICIENT_R_MULTIPLE_SAMPLE", result.reasons)
        self.assertIn("OPPORTUNITY_COUNT_NOT_PROVIDED", result.reasons)

    def test_rejects_non_finite_or_invalid_opportunity_data(self):
        with self.assertRaises(ValueError):
            BookMethodologyObserver.analyze_r_multiples((math.inf,))
        with self.assertRaises(ValueError):
            BookMethodologyObserver.analyze_r_multiples((1.0,), opportunities=0)

    def test_regime_report_never_pools_away_small_regimes(self):
        result = BookMethodologyObserver.analyze_r_by_regime(
            (("trend", 1.0), ("trend", -0.5), ("sideways", 2.0)),
            minimum_sample_per_regime=2,
        )
        self.assertEqual(result.status, "MORE_REGIME_EVIDENCE_REQUIRED")
        self.assertEqual(result.insufficient_regimes, ("SIDEWAYS",))
        self.assertEqual(tuple(name for name, _ in result.regimes), ("SIDEWAYS", "TREND"))
        self.assertFalse(result.risk_influence_allowed)


if __name__ == "__main__":
    unittest.main()
