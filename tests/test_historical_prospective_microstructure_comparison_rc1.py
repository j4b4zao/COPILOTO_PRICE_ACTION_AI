import json
from collections import Counter
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

import pytest

from tools.historical_microstructure_confluence_report import (
    HistoricalMicrostructureConfluenceReporter,
)
from tools.historical_prospective_microstructure_comparison import (
    VERSION,
    HistoricalProspectiveMicrostructureComparator,
)


def _historical():
    return HistoricalMicrostructureConfluenceReporter().build([
        SimpleNamespace(confluence={
            "state": state,
            "independent_evidence_count": independent,
            "correlated_evidence_count": correlated,
        })
        for state, independent, correlated in (
            ("CONFIRMED", 2, 0), ("CONFIRMED", 3, 1),
            ("CONFLICT", 1, 2), ("INSUFFICIENT_DATA", 0, 0),
        )
    ])


def _prospective():
    return {"prospective_microstructure": {
        "captured_samples": 3,
        "samples": [
            {"state": "CONFIRMED", "independent_evidence_count": 2,
             "correlated_evidence_count": 0, "conflict_count": 1},
            {"state": "CONFLICT", "independent_evidence_count": 3,
             "correlated_evidence_count": 2},
            {"state": "INSUFFICIENT_DATA", "independent_evidence_count": 1,
             "correlated_evidence_count": 0},
        ],
        "report": {"samples": 3, "high_quality_rate": 0.123456,
                   "three_source_rate": 0.234567, "average_confidence": 0.876543,
                   "conflict_rate": 0.6667, "correlation_rate": 0.9},
    }}


def _compare(historical=None, prospective=None, **kwargs):
    return HistoricalProspectiveMicrostructureComparator().compare(
        _historical() if historical is None else historical,
        _prospective() if prospective is None else prospective,
        **kwargs,
    )


def test_historical_rates():
    result = _compare()
    assert result.historical_samples == 4
    assert result.historical_confirmed_rate == 0.5
    assert result.historical_conflict_rate == 0.25
    assert result.historical_insufficient_rate == 0.25
    assert result.historical_two_or_more_independent_rate == 0.5
    assert result.historical_correlated_rate == 0.5


def test_prospective_rates_use_samples_and_aggregate_as_specified():
    result = _compare()
    assert result.prospective_samples == 3
    assert result.prospective_confirmed_rate == 0.3333
    assert result.prospective_conflict_rate == 0.3333
    assert result.prospective_insufficient_rate == 0.3333
    assert result.prospective_two_or_more_independent_rate == 0.6667
    assert result.prospective_correlated_rate == 0.3333
    assert result.prospective_high_quality_rate == 0.1235
    assert result.prospective_three_source_rate == 0.2346
    assert result.prospective_average_confidence == 0.8765


def test_deltas_are_prospective_minus_historical():
    result = _compare()
    assert result.confirmed_rate_delta == -0.1667
    assert result.conflict_rate_delta == 0.0833
    assert result.insufficient_rate_delta == 0.0833
    assert result.two_or_more_independent_rate_delta == 0.1667
    assert result.correlated_rate_delta == -0.1667


def test_deltas_round_after_subtraction():
    historical = {"samples": 6, "confirmed": 1}
    assert _compare(historical).confirmed_rate_delta == 0.1667


@pytest.mark.parametrize("key_type", [int, str])
@pytest.mark.parametrize("container", [dict, Counter])
def test_historical_evidence_integer_and_string_keys(key_type, container):
    historical = _historical().to_dict()
    for name in ("independent_evidence", "correlated_evidence"):
        historical[name] = container({key_type(k): v for k, v in historical[name].items()})
    assert _compare(historical).to_dict() == _compare().to_dict()


def test_attribute_objects_at_every_prospective_level_and_block_input():
    block = _prospective()["prospective_microstructure"]
    block["samples"] = [SimpleNamespace(**s) for s in block["samples"]]
    block["report"] = SimpleNamespace(**block["report"])
    evidence = SimpleNamespace(**block)
    wrapped = SimpleNamespace(prospective_microstructure=evidence)
    assert _compare(prospective=wrapped) == _compare()
    assert _compare(prospective=evidence) == _compare()


def test_zero_samples():
    result = _compare(
        HistoricalMicrostructureConfluenceReporter().build([]),
        {"prospective_microstructure": {"samples": [], "report": {}}},
    )
    assert result.historical_samples == result.prospective_samples == 0
    for name, value in result.to_dict().items():
        if name.endswith(("_rate", "_delta", "_confidence")):
            assert value == 0.0


@pytest.mark.parametrize("empty", [False, True])
def test_safety_and_status_are_fixed_even_with_unsafe_input_flags(empty):
    historical = {} if empty else _historical().to_dict()
    prospective = {"samples": [], "report": {}} if empty else _prospective()
    for value in (historical, prospective):
        value.update(status="APPROVED", research_only=False,
                     observational_only=False, promotion_allowed=True,
                     score_influence_allowed=True)
    result = _compare(historical, prospective)
    assert result.status == "DESCRIPTIVE_ONLY"
    assert result.research_only is True
    assert result.observational_only is True
    for name in ("predictive_claim_allowed", "score_influence_allowed",
                 "risk_influence_allowed", "decision_influence_allowed",
                 "alert_influence_allowed", "order_execution_allowed", "promotion_allowed"):
        assert getattr(result, name) is False
    with pytest.raises(FrozenInstanceError):
        result.status = "APPROVED"


def test_to_dict_version_labels_and_inputs_unchanged():
    historical = _historical().to_dict()
    prospective = _prospective()
    before = json.dumps([historical, prospective], sort_keys=True)
    result = _compare(historical, prospective,
                      historical_cohort_label="historico A",
                      prospective_cohort_label="prospectivo B")
    payload = result.to_dict()
    assert payload["version"] == VERSION == "RC1-HISTORICAL-PROSPECTIVE-MICROSTRUCTURE-COMPARISON"
    assert payload["historical_cohort_label"] == "historico A"
    assert payload["prospective_cohort_label"] == "prospectivo B"
    assert json.loads(json.dumps(payload)) == payload
    assert json.dumps([historical, prospective], sort_keys=True) == before
    payload["status"] = "CHANGED"
    assert result.status == "DESCRIPTIVE_ONLY"
