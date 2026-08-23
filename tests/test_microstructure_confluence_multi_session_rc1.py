from types import SimpleNamespace

import pytest

from analysis.replay.microstructure_confluence_multi_session import (
    MicrostructureConfluenceMultiSessionComparator,
)


def _report(samples=100, high=0.35, three=0.25, conflict=0.05, correlation=0.10, confidence=0.8, quality="STRONG_INDEPENDENT_CONFLUENCE"):
    return SimpleNamespace(
        samples=samples,
        high_quality_rate=high,
        three_source_rate=three,
        conflict_rate=conflict,
        correlation_rate=correlation,
        average_confidence=confidence,
        session_quality=quality,
    )


def test_requires_three_sessions():
    result = MicrostructureConfluenceMultiSessionComparator().compare([_report(), _report()])
    assert result.stability == "INSUFFICIENT_DATA"
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_requires_300_samples():
    reports = [_report(samples=90) for _ in range(3)]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.samples == 270
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_all_strong_sessions_are_stable_strong():
    result = MicrostructureConfluenceMultiSessionComparator().compare([_report(), _report(high=0.40), _report(high=0.45)])
    assert result.stability == "STABLE_STRONG"
    assert result.recommendation == "KEEP_OBSERVING"


def test_strong_and_promising_sessions_are_stable_promising():
    reports = [_report(), _report(quality="PROMISING", high=0.25), _report(high=0.40)]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_PROMISING"


def test_all_weak_sessions_are_stable_weak():
    reports = [_report(quality="WEAK", high=0.05, three=0.02) for _ in range(3)]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_WEAK"


def test_conflict_rate_degrades_comparison():
    reports = [_report(conflict=0.25), _report(conflict=0.20), _report(conflict=0.15)]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.weighted_conflict_rate == 0.2
    assert result.stability == "DEGRADED_BY_CONFLICT"
    assert result.recommendation == "REVIEW_CONFLICTS"


def test_high_quality_spread_breaks_stability():
    reports = [_report(high=0.10, quality="PROMISING"), _report(high=0.20, quality="PROMISING"), _report(high=0.40)]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.high_quality_spread == 0.3
    assert result.stability == "INCONSISTENT"
    assert result.recommendation == "REVIEW_STABILITY"


def test_weighted_metrics_use_sample_counts():
    reports = [
        _report(samples=100, high=0.5, three=0.4, correlation=0.2, confidence=0.9),
        _report(samples=200, high=0.25, three=0.1, correlation=0.1, confidence=0.7, quality="PROMISING"),
        _report(samples=100, high=0.0, three=0.0, correlation=0.0, confidence=0.5, quality="WEAK"),
    ]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.weighted_high_quality_rate == 0.25
    assert result.weighted_three_source_rate == 0.15
    assert result.weighted_correlation_rate == 0.1
    assert result.weighted_average_confidence == 0.7


def test_quality_counters_are_reported():
    reports = [_report(), _report(quality="PROMISING"), _report(quality="WEAK")]
    result = MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert result.strong_sessions == 1
    assert result.promising_sessions == 1
    assert result.weak_sessions == 1


def test_invalid_contract_rejected_and_input_not_mutated():
    reports = [_report(), _report(), _report()]
    before = list(reports)
    MicrostructureConfluenceMultiSessionComparator().compare(reports)
    assert reports == before
    with pytest.raises(TypeError):
        MicrostructureConfluenceMultiSessionComparator().compare([object()])
