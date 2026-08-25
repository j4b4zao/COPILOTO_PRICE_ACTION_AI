from types import SimpleNamespace

import pytest

from analysis.replay.order_flow_ab_multi_session import OrderFlowABMultiSessionComparator


def _report(samples=100, delta=0.8, effect="POSITIVE", grades=0, validity=0):
    return SimpleNamespace(
        samples=samples,
        average_delta=delta,
        dominant_effect=effect,
        grade_changes=grades,
        validity_changes=validity,
    )


def test_requires_three_sessions():
    result = OrderFlowABMultiSessionComparator().compare([_report(), _report()])
    assert result.stability == "INSUFFICIENT_DATA"
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_requires_300_samples():
    reports = [_report(samples=90) for _ in range(3)]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.samples == 270
    assert result.recommendation == "COLLECT_MORE_DATA"


def test_stable_positive_sessions():
    reports = [_report(delta=0.7), _report(delta=0.8), _report(delta=0.9)]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_POSITIVE"
    assert result.recommendation == "KEEP_OBSERVING"


def test_stable_negative_sessions():
    reports = [_report(delta=-0.7, effect="NEGATIVE"), _report(delta=-0.8, effect="NEGATIVE"), _report(delta=-0.9, effect="NEGATIVE")]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_NEGATIVE"


def test_stable_neutral_sessions():
    reports = [_report(delta=0.0, effect="NEUTRAL") for _ in range(3)]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.stability == "STABLE_NEUTRAL"


def test_conflicting_effects_are_inconsistent():
    reports = [_report(), _report(delta=-0.4, effect="NEGATIVE"), _report(delta=0.0, effect="NEUTRAL")]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.stability == "INCONSISTENT"
    assert result.recommendation == "REVIEW_BEFORE_ENABLE"


def test_excessive_spread_is_inconsistent():
    reports = [_report(delta=0.1), _report(delta=0.5), _report(delta=1.2)]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.delta_spread == 1.1
    assert result.stability == "INCONSISTENT"


def test_validity_change_forces_review():
    reports = [_report(), _report(validity=1), _report()]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.sessions_with_validity_changes == 1
    assert result.recommendation == "REVIEW_BEFORE_ENABLE"


def test_weighted_average_uses_sample_counts():
    reports = [_report(samples=100, delta=1.0), _report(samples=200, delta=0.5), _report(samples=100, delta=0.0)]
    result = OrderFlowABMultiSessionComparator().compare(reports)
    assert result.weighted_average_delta == 0.5
    assert result.samples == 400


def test_invalid_contract_is_rejected_and_input_is_not_mutated():
    reports = [_report(), _report(), _report()]
    before = list(reports)
    OrderFlowABMultiSessionComparator().compare(reports)
    assert reports == before
    with pytest.raises(TypeError):
        OrderFlowABMultiSessionComparator().compare([object()])
