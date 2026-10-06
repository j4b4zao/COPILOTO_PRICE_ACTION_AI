import json
import pytest
from external_context.providers.americas_oil_watch_wti_transport import AmericasOilWatchWTITransport

class R:
    def __init__(self,p): self.p=p
    def read(self): return json.dumps(self.p).encode()

def payload(**overrides):
    x={"quoteType":"intraday","quoteStatus":"current","provider":"Yahoo Finance (CL=F)",
       "dataSource":"Yahoo Finance (CL=F)","priceUsd":87.26,"changePct":-2.43,
       "observedAt":"2026-10-06T13:02:49.000Z","fetchedAt":"2026-10-06T13:12:50.897Z"}
    x.update(overrides); return x

def make(p):
    return AmericasOilWatchWTITransport(opener=lambda req,timeout:R(p))

def test_real_shape_normalizes_observation_not_fetch_time():
    x=make(payload()).fetch("CL=F")
    assert x=={"price":87.26,"change":-2.43,"timestamp":"2026-10-06T13:02:49+00:00"}

@pytest.mark.parametrize("changes",[
    {"quoteType":"daily"},{"quoteStatus":"stale"},
    {"provider":"EIA"},{"dataSource":"FRED"},
    {"observedAt":""},{"observedAt":"2026-10-06 13:02:49"},
    {"priceUsd":0},
])
def test_non_intraday_noncurrent_fallback_or_invalid_data_fails_closed(changes):
    assert make(payload(**changes)).fetch("CL=F") is None

def test_fetched_at_is_never_timestamp_fallback():
    assert make(payload(observedAt=None,fetchedAt="2026-10-06T13:12:50Z")).fetch("CL=F") is None

def test_only_clusd_upstream_symbol_is_accepted():
    with pytest.raises(ValueError):
        make(payload()).fetch("BZ=F")

def test_snapshot_declares_safety_semantics():
    s=AmericasOilWatchWTITransport().snapshot()
    assert s["observational_only"] is True
    assert s["requires_api_key"] is False
    assert s["daily_fallback_accepted"] is False
    assert s["timestamp_semantics"]=="observedAt_timezone_aware_iso8601"
