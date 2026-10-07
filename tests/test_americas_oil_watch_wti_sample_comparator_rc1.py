"""Offline WTI sample comparison contracts."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
import socket
from urllib.request import OpenerDirector

import pytest

from tools.americas_oil_watch_wti_sample_comparator_rc1 import run


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("network access is forbidden")
    monkeypatch.setattr(OpenerDirector, "open", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


def sample(reference="2026-10-07T14:24:11+00:00", observed="2026-10-07T13:01:03+00:00", http_age="247"):
    age = (datetime.fromisoformat(reference) - datetime.fromisoformat(observed)).total_seconds()
    return dict(name="AmericasOilWatchWTIFreshnessProbe", version="RC1",
        diagnostic_only=True, operational_influence_allowed=False,
        automatic_activation=False, fallback_allowed=False,
        endpoint="https://americasoilwatch.com/api/v1/wti", internal_asset="OIL", symbol="CL=F",
        provider="Yahoo Finance (CL=F)", dataSource="Yahoo Finance (CL=F)",
        maximum_staleness_seconds=3600, reference_timestamp=reference,
        timestamp=observed, raw_observedAt=observed, price=89.94, change=0.56,
        age_seconds=age, freshness_status="FUTURE" if age<0 else ("STALE" if age>3600 else "FRESH"),
        request_status="OK", validation_status="VALID", raw_quoteType="intraday", raw_quoteStatus="current",
        raw_other_timestamps={"fetchedAt":"2026-10-07T13:11:03.969Z"},
        raw_http_headers={"Age":http_age})


def pair():
    return [sample(), sample(reference="2026-10-07T14:33:50+00:00", http_age="225")]


def test_real_evidence_sorted_without_mutation_or_network():
    samples = list(reversed(pair()))
    original = deepcopy(samples)
    result = run(enabled=True,samples=samples)
    assert samples == original
    assert result["comparison_status"] == "COMPARED"
    assert result["diagnostic_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["automatic_activation"] is False
    assert result["fallback_allowed"] is False
    assert result["maximum_staleness_seconds"] == 3600
    assert result["cause_attribution"] is None
    comparison = result["comparisons"][0]
    assert comparison["state"] == "OBSERVATION_UNCHANGED"
    assert comparison["reference_timestamp_delta_seconds"] == 579
    assert comparison["observedAt_delta_seconds"] == 0
    assert comparison["fetchedAt_delta_seconds"] == 0
    assert comparison["age_seconds_delta"] == 579
    assert comparison["price_changed"] is False
    assert comparison["change_changed"] is False
    assert comparison["freshness_status_before"] == comparison["freshness_status_after"] == "STALE"
    assert (comparison["raw_http_age_before"],comparison["raw_http_age_after"]) == ("247","225")
    assert comparison["before_input_index"] == 1
    assert not {"score","risk","decision","alert","order","confidence"}.intersection(comparison)
    json.dumps(result, allow_nan=False)


def test_observation_advances_even_if_price_does_not():
    samples = pair()
    samples[1] = sample(reference="2026-10-07T14:33:50+00:00",observed="2026-10-07T13:02:03+00:00")
    result = run(enabled=True,samples=samples)["comparisons"][0]
    assert result["state"] == "OBSERVATION_ADVANCED"
    assert result["observedAt_delta_seconds"] == 60
    assert result["age_seconds_delta"] == 519


def test_reference_not_advancing():
    result = run(enabled=True,samples=[sample(),sample()])["comparisons"][0]
    assert result["reference_timestamp_delta_seconds"] == 0
    assert result["state"] == "INSUFFICIENT_EVIDENCE"


def test_observation_regression_is_insufficient():
    samples = pair()
    samples[1] = sample(reference="2026-10-07T14:33:50+00:00", observed="2026-10-07T13:00:03+00:00")
    assert run(enabled=True,samples=samples)["comparisons"][0]["state"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("field,value", [
    ("reference_timestamp","bad"),("reference_timestamp","2026-10-07T14:24:11"),
    ("timestamp","2026-10-07T13:01:03"),("raw_observedAt","bad"),
    ("symbol","BZ=F"),("dataSource","FRED"),("provider","EIA"),
    ("maximum_staleness_seconds",3601),("maximum_staleness_seconds",float("nan")),
    ("age_seconds",0),("freshness_status","FRESH"),("price",float("inf")),
    ("change",True),("raw_quoteType","daily"),("raw_quoteStatus","stale"),
    ("validation_status","INVALID"),("operational_influence_allowed",True),
    ("diagnostic_only",1),("endpoint","https://other.example"),
    ("raw_other_timestamps",{"fetchedAt":"2026-10-07T13:11:03"}),
    ("raw_other_timestamps",[]),("raw_http_headers",[]),
])
def test_incompatible_fields_are_insufficient(field,value):
    samples = pair()
    samples[1][field] = value
    result = run(enabled=True,samples=samples)
    assert result["comparison_status"] == "INSUFFICIENT_EVIDENCE"
    assert len(result["invalid_samples"]) == 1
    assert result["comparisons"] == []


def test_missing_fetched_at_does_not_replace_observation():
    samples = pair()
    samples[1]["raw_other_timestamps"] = {}
    result = run(enabled=True,samples=samples)["comparisons"][0]
    assert result["fetchedAt_delta_seconds"] is None
    assert result["state"] == "OBSERVATION_UNCHANGED"


@pytest.mark.parametrize("samples", [[],[sample()],[None], [{}]])
def test_insufficient_samples(samples):
    assert run(enabled=True,samples=samples)["comparison_status"] == "INSUFFICIENT_EVIDENCE"


def test_multiple_samples_compare_adjacent_chronologically():
    samples = pair()
    samples.append(sample(reference="2026-10-07T14:40:00+00:00"))
    result = run(enabled=True,samples=list(reversed(samples)))
    assert len(result["comparisons"]) == 2
    assert [item["reference_timestamp_delta_seconds"] for item in result["comparisons"]] == [579,370]


def test_enable_required():
    with pytest.raises(PermissionError):
        run(enabled=False,samples=pair())
