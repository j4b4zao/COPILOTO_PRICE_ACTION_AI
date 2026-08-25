from analysis.replay.microstructure_eligibility_multi_session_comparator import (
    MicrostructureEligibilityMultiSessionComparator,
    MicrostructureEligibilityMultiSessionReport,
)
from analysis.replay.microstructure_eligibility_session_report import (
    MicrostructureEligibilitySessionReport,
)


def _report(
    *,
    samples=100,
    strong=0.10,
    promising=0.20,
    conflict=0.05,
    correlation=0.20,
    confidence=0.75,
    state="STRONG_ELIGIBILITY_SIGNAL",
):
    return MicrostructureEligibilitySessionReport(
        samples=samples,
        not_eligible_rate=max(0.0, 1.0 - strong - promising),
        observable_rate=0.0,
        promising_rate=promising,
        strong_candidate_rate=strong,
        conflict_rate=conflict,
        correlation_rate=correlation,
        average_confidence=confidence,
        session_state=state,
        recommendation="KEEP_OBSERVING",
    )


def test_no_reports_returns_insufficient_data():
    result = MicrostructureEligibilityMultiSessionComparator().compare([])
    assert result.stability == "INSUFFICIENT_DATA"
    assert result.samples == 0


def test_requires_three_sessions():
    result = MicrostructureEligibilityMultiSessionComparator().compare([_report(), _report()])
    assert result.stability == "INSUFFICIENT_DATA"
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_requires_three_hundred_samples():
    reports = [_report(samples=90), _report(samples=90), _report(samples=90)]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.stability == "INSUFFICIENT_DATA"


def test_stable_strong_when_rates_are_consistent():
    reports = [
        _report(strong=0.10, promising=0.20),
        _report(strong=0.12, promising=0.20),
        _report(strong=0.11, promising=0.19),
    ]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_STRONG"
    assert result.recommendation == "KEEP_OBSERVING"


def test_stable_promising_without_enough_strong_rate():
    reports = [
        _report(strong=0.04, promising=0.18, state="PROMISING_ELIGIBILITY_SIGNAL"),
        _report(strong=0.05, promising=0.17, state="PROMISING_ELIGIBILITY_SIGNAL"),
        _report(strong=0.03, promising=0.19, state="PROMISING_ELIGIBILITY_SIGNAL"),
    ]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_PROMISING"


def test_stable_weak_when_eligible_rate_is_low():
    reports = [
        _report(strong=0.01, promising=0.08, state="WEAK_ELIGIBILITY_SIGNAL"),
        _report(strong=0.02, promising=0.07, state="WEAK_ELIGIBILITY_SIGNAL"),
        _report(strong=0.01, promising=0.09, state="WEAK_ELIGIBILITY_SIGNAL"),
    ]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_WEAK"


def test_weighted_conflict_degrades_result():
    reports = [
        _report(conflict=0.25, state="DEGRADED_BY_CONFLICT"),
        _report(conflict=0.20, state="DEGRADED_BY_CONFLICT"),
        _report(conflict=0.15, state="PROMISING_ELIGIBILITY_SIGNAL"),
    ]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.stability == "DEGRADED_BY_CONFLICT"
    assert result.recommendation == "REVIEW_CONFLICTS"


def test_excessive_strong_spread_is_inconsistent():
    reports = [
        _report(strong=0.02, promising=0.28),
        _report(strong=0.15, promising=0.15),
        _report(strong=0.12, promising=0.18),
    ]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.stability == "INCONSISTENT"
    assert result.recommendation == "REVIEW_STABILITY"


def test_weighted_metrics_use_sample_counts():
    reports = [
        _report(samples=100, strong=0.10, promising=0.20, confidence=0.70),
        _report(samples=200, strong=0.20, promising=0.20, confidence=0.80),
        _report(samples=100, strong=0.10, promising=0.20, confidence=0.70),
    ]
    result = MicrostructureEligibilityMultiSessionComparator().compare(reports)
    assert result.weighted_strong_candidate_rate == 0.15
    assert result.weighted_average_confidence == 0.75


def test_report_is_frozen_and_invalid_contract_is_rejected():
    result = MicrostructureEligibilityMultiSessionReport()
    try:
        result.samples = 1
    except Exception:
        pass
    else:
        raise AssertionError("Relatório deveria ser imutável")

    try:
        MicrostructureEligibilityMultiSessionComparator().compare([object()])
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError esperado")
