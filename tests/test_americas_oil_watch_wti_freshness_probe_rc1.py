"""Offline-only WTI freshness and no-fallback contract tests."""
import json
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import OpenerDirector

import pytest

from tools.americas_oil_watch_wti_freshness_probe_rc1 import run, URL
from external_context.providers.resolved_five_observational_configuration import build_resolved_five_observational_router

REFERENCE = "2026-10-07T13:56:25+00:00"


@pytest.fixture(autouse=True)
def prohibit_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("network is forbidden in offline tests")
    monkeypatch.setattr(OpenerDirector, "open", forbidden)


def payload(**overrides):
    result = dict(provider="Yahoo Finance (CL=F)", dataSource="Yahoo Finance (CL=F)",
                  quoteType="intraday", quoteStatus="current", priceUsd=87.26,
                  changePct=-2.43, observedAt="2026-10-07T13:56:16Z",
                  fetchedAt="2026-10-07T13:56:25Z")
    result.update(overrides)
    return result


class Response:
    headers = {"Age": "600", "Cache-Control": "max-age=600"}
    def __init__(self, data):
        self.data = data
        self.closed = False
    def read(self):
        return json.dumps(self.data).encode()
    def close(self):
        self.closed = True


def probe(data):
    response = Response(data)
    calls = []
    def opener(request, timeout):
        assert request.full_url == URL == "https://americasoilwatch.com/api/v1/wti"
        assert request.get_method() == "GET"
        assert timeout == 5
        calls.append(request.full_url)
        return response
    result = run(enabled=True, reference_timestamp=REFERENCE,
                 maximum_staleness_seconds=3600, opener=opener)
    assert calls == [URL]
    assert response.closed
    assert result["diagnostic_only"] is True
    assert result["operational_influence_allowed"] is False
    assert result["automatic_activation"] is False
    assert result["fallback_allowed"] is False
    return result


@pytest.mark.parametrize("age,status", [(-1,"FUTURE"),(-3,"FUTURE"),(0,"FRESH"),
                                       (9,"FRESH"),(3600,"FRESH"),(3601,"STALE")])
def test_freshness_boundaries(age, status):
    observed = datetime.fromisoformat(REFERENCE) - timedelta(seconds=age)
    result = probe(payload(observedAt=observed.isoformat()))
    assert result["age_seconds"] == age
    assert result["freshness_status"] == status
    assert result["symbol"] == "CL=F"
    assert result["price"] == 87.26 and result["change"] == -2.43


def test_offset_converts_to_utc_and_other_evidence_never_overrides():
    result = probe(payload(observedAt="2026-10-07T10:56:16-03:00"))
    assert result["timestamp"] == "2026-10-07T13:56:16+00:00"
    assert result["raw_observedAt"] == "2026-10-07T10:56:16-03:00"
    assert result["age_seconds"] == 9
    assert result["raw_other_timestamps"] == {"fetchedAt":"2026-10-07T13:56:25Z"}
    assert result["raw_http_headers"]["Age"] == "600"


@pytest.mark.parametrize("changes,status", [
    ({"observedAt":"2026-10-07 13:56:16"},"INVALID_OBSERVED_AT"),
    ({"observedAt":None},"INVALID_OBSERVED_AT"),
    ({"observedAt":"bad"},"INVALID_OBSERVED_AT"),
    ({"symbol":"BZ=F"},"INVALID_IDENTITY"),
    ({"provider":"Yahoo Finance (BZ=F)"},"INVALID_UPSTREAM"),
    ({"dataSource":"FRED"},"INVALID_UPSTREAM"),
    ({"provider":"untrusted Yahoo Finance (CL=F)"},"INVALID_UPSTREAM"),
    ({"quoteType":"daily"},"INCOMPATIBLE_QUOTE"),
    ({"quoteStatus":"stale"},"INCOMPATIBLE_QUOTE"),
    ({"priceUsd":0},"INVALID_PAYLOAD"),
    ({"priceUsd":float("nan")},"INVALID_PAYLOAD"),
    ({"changePct":float("inf")},"INVALID_PAYLOAD"),
    ({"priceUsd":True},"INVALID_PAYLOAD"),
])
def test_invalid_observations_fail_closed(changes,status):
    result = probe(payload(**changes))
    json.dumps(result, allow_nan=False)
    assert result["validation_status"] == status
    assert result["freshness_status"] == "UNAVAILABLE"
    assert result["age_seconds"] is None and result["timestamp"] is None


@pytest.mark.parametrize("data", [[],None,{}, {"priceUsd":"bad"}])
def test_invalid_payload(data):
    assert probe(data)["freshness_status"] == "UNAVAILABLE"


@pytest.mark.parametrize("threshold", [0,-1,float("nan"),float("inf"),float("-inf")])
def test_invalid_threshold_before_request(threshold):
    with pytest.raises(ValueError):
        run(enabled=True, reference_timestamp=REFERENCE, maximum_staleness_seconds=threshold)


@pytest.mark.parametrize("reference", ["2026-10-07T13:56:25", "bad"])
def test_reference_must_be_explicit_and_aware(reference):
    with pytest.raises(ValueError):
        run(enabled=True, reference_timestamp=reference, maximum_staleness_seconds=3600)


def test_enable_required_before_request():
    with pytest.raises(PermissionError):
        run(enabled=False, reference_timestamp=REFERENCE, maximum_staleness_seconds=3600)


@pytest.mark.parametrize("error,status", [
    (HTTPError(URL,402,"restricted",{},None),"HTTP_ERROR"),
    (URLError("offline"),"TRANSPORT_ERROR"),
    (TimeoutError(),"TRANSPORT_ERROR"),
])
def test_transport_errors(error,status):
    def opener(*args,**kwargs):
        raise error
    result = run(enabled=True,reference_timestamp=REFERENCE,
                 maximum_staleness_seconds=3600,opener=opener)
    assert result["request_status"] == status
    assert result["freshness_status"] == "UNAVAILABLE"


def test_invalid_json():
    class BadResponse(Response):
        def read(self):
            return b"not json"
    result = run(enabled=True,reference_timestamp=REFERENCE,
                 maximum_staleness_seconds=3600,opener=lambda *a,**k:BadResponse(None))
    assert result["request_status"] == "INVALID_JSON"


def test_oil_route_repeats_request_and_never_falls_back_or_reuses_old_data():
    calls = []
    data = payload(observedAt="2026-10-06T13:02:49Z")
    def forbidden(*args,**kwargs):
        pytest.fail("OIL must not call another source")
    def oil(request,timeout):
        calls.append(request.full_url)
        return Response(data if len(calls) == 1 else [])
    router = build_resolved_five_observational_router(fmp_api_key="offline",
        twelvedata_api_key="offline",fmp_opener=forbidden,twelvedata_opener=forbidden,oil_opener=oil)
    first = router.fetch("OIL")
    assert first["timestamp"] == "2026-10-06T13:02:49+00:00"
    assert probe(data)["freshness_status"] == "STALE"
    assert router.fetch("OIL") is None
    assert calls == [URL,URL]

