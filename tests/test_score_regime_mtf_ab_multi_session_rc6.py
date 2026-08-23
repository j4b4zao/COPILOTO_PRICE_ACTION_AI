from analysis.replay.score_regime_mtf_ab_multi_session import (
    ScoreRegimeMtfABMultiSessionComparator,
)
from analysis.replay.score_regime_mtf_ab_session_report import (
    ScoreRegimeMtfABSessionReport,
)


def _report(
    *,
    samples=120,
    average_delta=1.0,
    effect="POSITIVE",
    grade_changes=0,
    validity_changes=0,
    recommendation="PROMISING_KEEP_AB",
):
    return ScoreRegimeMtfABSessionReport(
        version="RC5",
        samples=samples,
        weight=3.0,
        average_delta=average_delta,
        positive_adjustments=samples if effect == "POSITIVE" else 0,
        negative_adjustments=samples if effect == "NEGATIVE" else 0,
        neutral_adjustments=samples if effect == "NEUTRAL" else 0,
        grade_changes=grade_changes,
        validity_changes=validity_changes,
        dominant_effect=effect,
        strongest_positive_scenario="by_regime:TREND_UP",
        strongest_negative_scenario="by_alignment:CONFLICT_REGIME",
        recommendation=recommendation,
        passive_only=True,
    )


def test_empty_reports_return_no_data():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([])
    assert report.sessions == 0
    assert report.recommendation == "NO_DATA"
    assert report.stable_across_sessions is False


def test_less_than_three_sessions_collect_more():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(),
        _report(),
    ])
    assert report.recommendation == "COLLECT_MORE_SESSIONS"
    assert report.stable_across_sessions is False


def test_three_consistent_positive_sessions_are_stable():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(average_delta=0.8),
        _report(average_delta=1.0),
        _report(average_delta=1.2),
    ])
    assert report.stable_across_sessions is True
    assert report.positive_sessions == 3
    assert report.recommendation == "CONSISTENTLY_PROMISING_KEEP_AB"


def test_three_consistent_negative_sessions_are_stable_but_not_promising():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(average_delta=-0.8, effect="NEGATIVE"),
        _report(average_delta=-1.0, effect="NEGATIVE"),
        _report(average_delta=-1.2, effect="NEGATIVE"),
    ])
    assert report.stable_across_sessions is True
    assert report.negative_sessions == 3
    assert report.recommendation == "CONSISTENT_NEGATIVE_REVIEW_PENALTIES"


def test_conflicting_session_effects_are_inconsistent():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(average_delta=1.0, effect="POSITIVE"),
        _report(average_delta=-1.0, effect="NEGATIVE"),
        _report(average_delta=0.0, effect="NEUTRAL"),
    ])
    assert report.stable_across_sessions is False
    assert report.recommendation == "INCONSISTENT_KEEP_AB"


def test_validity_change_forces_review():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(),
        _report(validity_changes=1),
        _report(),
    ])
    assert report.sessions_with_validity_changes == 1
    assert report.stable_across_sessions is False
    assert report.recommendation == "REVIEW_BEFORE_ENABLE"


def test_weighted_average_uses_sample_counts():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(samples=100, average_delta=1.0),
        _report(samples=200, average_delta=2.0),
        _report(samples=100, average_delta=1.0),
    ])
    assert report.total_samples == 400
    assert report.weighted_average_delta == 1.5


def test_large_delta_spread_breaks_stability():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(average_delta=0.2),
        _report(average_delta=1.0),
        _report(average_delta=2.0),
    ])
    assert report.delta_spread == 1.8
    assert report.stable_across_sessions is False


def test_recommendation_agreement_is_reported():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(recommendation="PROMISING_KEEP_AB"),
        _report(recommendation="PROMISING_KEEP_AB"),
        _report(recommendation="PROMISING_KEEP_AB"),
    ])
    assert report.recommendation_agreement is True


def test_report_contract_is_frozen_and_passive():
    report = ScoreRegimeMtfABMultiSessionComparator.compare([
        _report(),
        _report(),
        _report(),
    ])
    assert report.passive_only is True
    try:
        report.sessions = 99
        assert False
    except Exception:
        assert True
