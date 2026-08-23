from types import SimpleNamespace

import pytest

from analysis.replay.book_depth_ab_multi_session import BookDepthABMultiSessionComparator


def _report(
    samples=100,
    delta=0.3,
    effect="POSITIVE",
    grades=0,
    validity=0,
    independent_samples=60,
    independent_delta=0.4,
    correlated_samples=40,
    correlated_delta=0.15,
):
    return SimpleNamespace(
        samples=samples,
        average_delta=delta,
        dominant_effect=effect,
        grade_changes=grades,
        validity_changes=validity,
        independent_samples=independent_samples,
        independent_average_delta=independent_delta,
        correlated_samples=correlated_samples,
        correlated_average_delta=correlated_delta,
    )


def test_requires_three_sessions():
    result = BookDepthABMultiSessionComparator().compare([_report(), _report()])
    assert result.stability == "INSUFFICIENT_DATA"
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_requires_300_samples():
    result = BookDepthABMultiSessionComparator().compare([_report(samples=90) for _ in range(3)])
    assert result.samples == 270
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_stable_positive_sessions():
    reports = [_report(delta=0.20), _report(delta=0.30), _report(delta=0.40)]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_POSITIVE"
    assert result.recommendation == "KEEP_OBSERVING"


def test_stable_negative_sessions():
    reports = [
        _report(delta=-0.20, effect="NEGATIVE"),
        _report(delta=-0.30, effect="NEGATIVE"),
        _report(delta=-0.40, effect="NEGATIVE"),
    ]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_NEGATIVE"


def test_stable_neutral_sessions():
    reports = [_report(delta=0.0, effect="NEUTRAL") for _ in range(3)]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_NEUTRAL"


def test_conflicting_effects_are_inconsistent():
    reports = [
        _report(effect="POSITIVE"),
        _report(delta=-0.2, effect="NEGATIVE"),
        _report(delta=0.0, effect="NEUTRAL"),
    ]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.stability == "INCONSISTENT"
    assert result.recommendation == "REVIEW_BEFORE_ENABLE"


def test_excessive_spread_is_inconsistent():
    reports = [_report(delta=0.0), _report(delta=0.2), _report(delta=0.6)]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.delta_spread == 0.6
    assert result.stability == "INCONSISTENT"


def test_validity_change_forces_review():
    reports = [_report(), _report(validity=1), _report()]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.sessions_with_validity_changes == 1
    assert result.recommendation == "REVIEW_BEFORE_ENABLE"


def test_weighted_totals_and_independent_vs_correlated():
    reports = [
        _report(samples=100, delta=0.4, independent_samples=80, independent_delta=0.5, correlated_samples=20, correlated_delta=0.1),
        _report(samples=200, delta=0.2, independent_samples=100, independent_delta=0.3, correlated_samples=100, correlated_delta=0.1),
        _report(samples=100, delta=0.0, independent_samples=20, independent_delta=0.1, correlated_samples=80, correlated_delta=-0.05),
    ]
    result = BookDepthABMultiSessionComparator().compare(reports)
    assert result.weighted_average_delta == 0.2
    assert result.weighted_independent_delta == 0.37
    assert result.weighted_correlated_delta == 0.04


def test_invalid_contract_is_rejected_and_input_is_not_mutated():
    reports = [_report(), _report(), _report()]
    before = list(reports)
    BookDepthABMultiSessionComparator().compare(reports)
    assert reports == before
    with pytest.raises(TypeError):
        BookDepthABMultiSessionComparator().compare([object()])
