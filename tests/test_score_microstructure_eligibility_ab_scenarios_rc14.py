from analysis.replay.score_microstructure_eligibility_ab_recorder import (
    ScoreMicrostructureEligibilityABRecorder,
    ScoreMicrostructureEligibilityABSample,
)


def _sample(**overrides):
    values = dict(
        baseline_total=80.0, adjusted_total=81.5, delta=1.5,
        baseline_grade="A", adjusted_grade="A", eligibility_state="STRONG_CANDIDATE",
        eligibility_reason="THREE_INDEPENDENT_HIGH_CONFIDENCE", confluence_quality="HIGH",
        confidence=0.85, confidence_bucket="HIGH", independent_evidence_count=3,
        correlated_evidence_count=0, conflict_count=0, correlation_bucket="INDEPENDENT",
        correlation_factor=1.0, raw_adjustment=1.5, adjustment=1.5,
    )
    values.update(overrides)
    return ScoreMicrostructureEligibilityABSample(**values)


def test_scenario_summary_groups_eligibility():
    r = ScoreMicrostructureEligibilityABRecorder()
    r._append(_sample())
    r._append(_sample(eligibility_state="PROMISING", delta=0.75, adjustment=0.75))
    grouped = r.scenario_summary()["by_eligibility"]
    assert grouped["STRONG_CANDIDATE"]["samples"] == 1
    assert grouped["PROMISING"]["samples"] == 1


def test_groups_quality():
    r = ScoreMicrostructureEligibilityABRecorder(); r._append(_sample())
    assert r.scenario_summary()["by_quality"]["HIGH"]["samples"] == 1


def test_groups_independent_evidence():
    r = ScoreMicrostructureEligibilityABRecorder(); r._append(_sample())
    assert r.scenario_summary()["by_independent_evidence"]["3"]["samples"] == 1


def test_groups_correlation():
    r = ScoreMicrostructureEligibilityABRecorder()
    r._append(_sample(correlated_evidence_count=1, correlation_bucket="CORRELATED", delta=0.38))
    assert r.scenario_summary()["by_correlation"]["CORRELATED"]["correlated_samples"] == 1


def test_groups_confidence_bucket():
    r = ScoreMicrostructureEligibilityABRecorder(); r._append(_sample())
    assert r.scenario_summary()["by_confidence"]["HIGH"]["average_confidence"] == 0.85


def test_groups_conflict_count():
    r = ScoreMicrostructureEligibilityABRecorder()
    r._append(_sample(conflict_count=1, delta=0.0, adjustment=0.0))
    assert r.scenario_summary()["by_conflict"]["1"]["conflict_samples"] == 1


def test_combined_scenario_filter():
    r = ScoreMicrostructureEligibilityABRecorder(); r._append(_sample())
    r._append(_sample(eligibility_state="PROMISING", independent_evidence_count=2, delta=0.75))
    result = r.scenario(eligibility="strong_candidate", quality="high", independent=3,
                        correlation="independent", confidence="high", conflict=0)
    assert result["samples"] == 1
    assert result["average_delta"] == 1.5


def test_metrics_average_independent_and_correlated():
    r = ScoreMicrostructureEligibilityABRecorder()
    r._append(_sample())
    r._append(_sample(independent_evidence_count=2, correlated_evidence_count=1,
                      correlation_bucket="CORRELATED", delta=0.38))
    summary = r.summary()
    assert summary["average_independent_evidence"] == 2.5
    assert summary["average_correlated_evidence"] == 0.5


def test_empty_scenario_is_safe():
    r = ScoreMicrostructureEligibilityABRecorder()
    result = r.scenario(eligibility="STRONG_CANDIDATE")
    assert result["samples"] == 0
    assert result["average_delta"] == 0.0


def test_retention_still_applies_with_scenarios():
    r = ScoreMicrostructureEligibilityABRecorder(max_samples=2)
    r._append(_sample(delta=1.0)); r._append(_sample(delta=1.2)); r._append(_sample(delta=1.5))
    assert r.size == 2
    assert r.summary()["samples"] == 2
