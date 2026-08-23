from types import SimpleNamespace

import pytest

from analysis.replay.microstructure_eligibility_policy import MicrostructureEligibilityPolicy


def _snapshot(state="CONFIRMED", quality="HIGH", confidence=0.8, independent=3, correlated=0, conflicts=0):
    return SimpleNamespace(
        state=state,
        confluence_quality=quality,
        confidence=confidence,
        independent_evidence_count=independent,
        correlated_evidence_count=correlated,
        conflict_count=conflicts,
    )


def test_three_independent_high_confidence_is_strong_candidate():
    result = MicrostructureEligibilityPolicy().evaluate(_snapshot())
    assert result.state == "STRONG_CANDIDATE"


def test_two_sources_medium_is_promising():
    result = MicrostructureEligibilityPolicy().evaluate(
        _snapshot(quality="MEDIUM", confidence=0.7, independent=2)
    )
    assert result.state == "PROMISING"


def test_one_source_can_be_observable():
    result = MicrostructureEligibilityPolicy().evaluate(
        _snapshot(quality="LOW", confidence=0.55, independent=1)
    )
    assert result.state == "OBSERVABLE"


def test_low_confidence_is_not_eligible():
    result = MicrostructureEligibilityPolicy().evaluate(
        _snapshot(quality="LOW", confidence=0.3, independent=1)
    )
    assert result.state == "NOT_ELIGIBLE"


def test_conflict_blocks_eligibility():
    result = MicrostructureEligibilityPolicy().evaluate(
        _snapshot(state="CONFLICT", conflicts=1)
    )
    assert result.state == "NOT_ELIGIBLE"
    assert result.reason == "CONFLICT_PRESENT"


def test_insufficient_data_is_not_eligible():
    result = MicrostructureEligibilityPolicy().evaluate(
        _snapshot(state="INSUFFICIENT_DATA", independent=0)
    )
    assert result.state == "NOT_ELIGIBLE"
    assert result.reason == "INSUFFICIENT_DATA"


def test_correlation_downgrades_strong_candidate_to_promising():
    result = MicrostructureEligibilityPolicy().evaluate(_snapshot(correlated=1))
    assert result.state == "PROMISING"
    assert result.reason == "CORRELATED_EVIDENCE_DISCOUNT"


def test_confidence_is_clamped():
    result = MicrostructureEligibilityPolicy().evaluate(_snapshot(confidence=2.0))
    assert result.confidence == 1.0


def test_invalid_contract_is_rejected():
    with pytest.raises(TypeError):
        MicrostructureEligibilityPolicy().evaluate(object())


def test_decision_is_passive_and_serializable():
    result = MicrostructureEligibilityPolicy().evaluate(_snapshot())
    assert result.passive_only is True
    assert result.to_dict()["state"] == "STRONG_CANDIDATE"
