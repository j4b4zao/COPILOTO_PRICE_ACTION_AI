from analysis.replay.external_context_ab_multi_session_comparator import (
    ExternalContextABMultiSessionComparator,
)
from analysis.replay.external_context_ab_session_report import (
    ExternalContextABSessionReport,
)


def _report(
    *,
    samples=100,
    delta=0.5,
    effect="POSITIVE",
    grade_changes=0,
    validity_changes=0,
    recommendation="KEEP_OBSERVING",
):
    return ExternalContextABSessionReport(
        samples=samples,
        average_delta=delta,
        dominant_effect=effect,
        grade_changes=grade_changes,
        validity_changes=validity_changes,
        recommendation=recommendation,
    )


def test_requires_three_sessions():
    report = ExternalContextABMultiSessionComparator().compare([_report(), _report()])
    assert report.stability == "INSUFFICIENT_DATA"
    assert report.recommendation == "COLLECT_MORE_DATA"


def test_requires_300_samples():
    reports = [_report(samples=50), _report(samples=50), _report(samples=50)]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.total_samples == 150
    assert result.stability == "INSUFFICIENT_DATA"


def test_three_positive_sessions_are_stable_positive():
    reports = [_report(delta=0.4), _report(delta=0.5), _report(delta=0.6)]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_POSITIVE"
    assert result.positive_sessions == 3


def test_three_negative_sessions_are_stable_negative():
    reports = [
        _report(delta=-0.4, effect="NEGATIVE"),
        _report(delta=-0.5, effect="NEGATIVE"),
        _report(delta=-0.6, effect="NEGATIVE"),
    ]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_NEGATIVE"
    assert result.negative_sessions == 3


def test_neutral_sessions_are_stable_neutral():
    reports = [
        _report(delta=0.0, effect="NEUTRAL"),
        _report(delta=0.0, effect="NEUTRAL"),
        _report(delta=0.0, effect="NEUTRAL"),
    ]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_NEUTRAL"


def test_conflicting_effects_are_inconsistent():
    reports = [
        _report(delta=0.5, effect="POSITIVE"),
        _report(delta=-0.4, effect="NEGATIVE"),
        _report(delta=0.0, effect="NEUTRAL"),
    ]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.stability == "INCONSISTENT"


def test_large_delta_spread_is_unstable():
    reports = [_report(delta=0.1), _report(delta=0.2), _report(delta=1.5)]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.delta_spread == 1.4
    assert result.stability == "UNSTABLE"


def test_validity_change_forces_review():
    reports = [_report(), _report(), _report(validity_changes=1, recommendation="REVIEW_BEFORE_ENABLE")]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.validity_change_sessions == 1
    assert result.recommendation == "REVIEW_BEFORE_ENABLE"


def test_weighted_average_uses_session_samples():
    reports = [
        _report(samples=100, delta=1.0),
        _report(samples=100, delta=1.0),
        _report(samples=200, delta=0.0, effect="NEUTRAL"),
    ]
    result = ExternalContextABMultiSessionComparator().compare(reports)
    assert result.total_samples == 400
    assert result.weighted_average_delta == 0.5


def test_comparison_is_readonly_and_rejects_invalid_contract():
    comparator = ExternalContextABMultiSessionComparator()
    reports = [_report(), _report(), _report()]
    before = tuple(reports)
    comparator.compare(reports)
    assert tuple(reports) == before

    try:
        comparator.compare([object()])
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError esperado")
