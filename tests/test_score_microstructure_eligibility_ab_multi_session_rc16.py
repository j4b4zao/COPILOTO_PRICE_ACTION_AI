from analysis.replay.score_microstructure_eligibility_ab_multi_session import (
    ScoreMicrostructureEligibilityABMultiSessionComparator,
)
from analysis.replay.score_microstructure_eligibility_ab_session_report import (
    ScoreMicrostructureEligibilityABSessionReport,
)


def _report(**overrides):
    values = dict(
        classification="STRONG_PASSIVE_SIGNAL", recommendation="KEEP_OBSERVING",
        samples=100, average_delta=0.8, strong_candidate_rate=0.18,
        promising_rate=0.22, independent_strong_rate=0.16,
        correlated_rate=0.10, conflict_rate=0.05, grade_change_rate=0.01,
        validity_change_rate=0.0, average_confidence=0.82,
    )
    values.update(overrides)
    return ScoreMicrostructureEligibilityABSessionReport(**values)


def test_no_sessions_is_insufficient():
    result = ScoreMicrostructureEligibilityABMultiSessionComparator().compare([])
    assert result.classification == "INSUFFICIENT_DATA"
    assert result.samples == 0


def test_requires_three_sessions():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    result = c.compare([_report(), _report()])
    assert result.classification == "INSUFFICIENT_DATA"


def test_requires_300_samples():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(samples=90), _report(samples=90), _report(samples=90)]
    assert c.compare(reports).classification == "INSUFFICIENT_DATA"


def test_stable_strong():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    result = c.compare([_report(), _report(average_delta=0.9), _report(average_delta=0.85)])
    assert result.classification == "STABLE_STRONG"
    assert result.recommendation == "KEEP_OBSERVING"


def test_stable_promising():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(independent_strong_rate=0.10, strong_candidate_rate=0.12, promising_rate=0.25)] * 3
    assert c.compare(reports).classification == "STABLE_PROMISING"


def test_stable_weak():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(independent_strong_rate=0.05, strong_candidate_rate=0.08, promising_rate=0.12)] * 3
    assert c.compare(reports).classification == "STABLE_WEAK"


def test_conflict_degrades():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(conflict_rate=0.25)] * 3
    result = c.compare(reports)
    assert result.classification == "DEGRADED_BY_CONFLICT"
    assert result.recommendation == "REVIEW_CONFLICTS"


def test_validity_change_forces_review():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(validity_change_rate=0.01)] * 3
    result = c.compare(reports)
    assert result.classification == "REVIEW_VALIDITY_CHANGES"
    assert result.recommendation == "REVIEW_BEFORE_ENABLE"


def test_large_delta_spread_is_inconsistent():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(average_delta=0.2), _report(average_delta=0.8), _report(average_delta=1.1)]
    assert c.compare(reports).classification == "INCONSISTENT"


def test_weighting_uses_session_size():
    c = ScoreMicrostructureEligibilityABMultiSessionComparator()
    reports = [_report(samples=100, average_delta=0.5), _report(samples=100, average_delta=0.5),
               _report(samples=200, average_delta=1.0)]
    result = c.compare(reports)
    assert result.samples == 400
    assert result.weighted_average_delta == 0.75
