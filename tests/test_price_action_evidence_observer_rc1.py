import pytest

from analysis.research.price_action_evidence_observer import (
    PriceActionEvidence,
    PriceActionEvidenceObserver,
)


def _item(*, session="S1", pattern="DOJI", regime="SIDEWAYS", timeframe="M1", location="MID", horizon=1, ret=0.0, volume=None, baseline=None):
    return PriceActionEvidence(
        session_id=session,
        pattern=pattern,
        regime=regime,
        timeframe=timeframe,
        location_context=location,
        horizon_steps=horizon,
        forward_return=ret,
        volume=volume,
        baseline_volume=baseline,
    )


def test_separates_pattern_regime_timeframe_and_location_without_signal():
    report = PriceActionEvidenceObserver.analyze(
        (
            _item(ret=0.01, volume=120, baseline=100),
            _item(ret=-0.02, volume=80, baseline=100),
            _item(regime="TREND", ret=0.03),
        ),
        minimum_sample_per_bucket=2,
        minimum_sessions_per_bucket=1,
    )
    assert len(report.buckets) == 2
    sideways = next(bucket for bucket in report.buckets if "SIDEWAYS" in bucket.key)
    assert sideways.observations == 2
    assert sideways.mean_forward_return == pytest.approx(-0.005)
    assert sideways.positive_rate == 0.5
    assert sideways.mean_volume_ratio == pytest.approx(1.0)
    assert report.status == "MORE_EVIDENCE_REQUIRED"


def test_ready_requires_minimum_sample_in_every_context_bucket():
    report = PriceActionEvidenceObserver.analyze(
        (_item(session="S1", ret=0.01), _item(session="S2", ret=-0.01)),
        minimum_sample_per_bucket=2,
        minimum_sessions_per_bucket=2,
    )
    assert report.status == "EVIDENCE_READY"
    assert report.insufficient_buckets == ()
    assert report.buckets[0].sessions == 2
    assert report.buckets[0].maximum_session_share == 0.5


def test_does_not_mix_forward_horizons():
    report = PriceActionEvidenceObserver.analyze(
        (_item(horizon=1), _item(horizon=5)),
        minimum_sample_per_bucket=1,
        minimum_sessions_per_bucket=1,
    )
    assert {bucket.key.rsplit("|", 1)[-1] for bucket in report.buckets} == {"H1", "H5"}


def test_empty_and_partial_volume_are_explicitly_not_ready_or_invalid():
    report = PriceActionEvidenceObserver.analyze(())
    assert report.status == "MORE_EVIDENCE_REQUIRED"
    assert report.reasons == ("NO_PRICE_ACTION_EVIDENCE",)
    with pytest.raises(ValueError, match="juntos"):
        _item(volume=10)


def test_all_operational_influence_is_hard_disabled():
    report = PriceActionEvidenceObserver.analyze(
        (_item(),), minimum_sample_per_bucket=1, minimum_sessions_per_bucket=1
    )
    assert report.observational_only is True
    assert report.predictive_claim_allowed is False
    assert report.score_influence_allowed is False
    assert report.risk_influence_allowed is False
    assert report.decision_influence_allowed is False
    assert report.alert_influence_allowed is False
    assert report.order_execution_allowed is False


def test_occurrence_count_alone_does_not_replace_session_recurrence():
    report = PriceActionEvidenceObserver.analyze(
        tuple(_item(session="ONLY") for _ in range(30)),
        minimum_sample_per_bucket=30,
        minimum_sessions_per_bucket=3,
    )
    assert report.buckets[0].sample_sufficient is True
    assert report.buckets[0].cross_session_sufficient is False
    assert report.buckets[0].maximum_session_share == 1.0
    assert "INSUFFICIENT_CROSS_SESSION_RECURRENCE" in report.reasons
