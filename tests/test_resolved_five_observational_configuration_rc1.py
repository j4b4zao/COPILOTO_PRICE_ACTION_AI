import json
from external_context.providers.resolved_five_observational_configuration import build_resolved_five_observational_router,snapshot
class R:
    def __init__(self,p):self.p=p
    def read(self):return json.dumps(self.p).encode()
def fmp(req,timeout):
    from urllib.parse import parse_qs,urlparse
    s=parse_qs(urlparse(req.full_url).query)["symbol"][0]
    return R([{"symbol":s,"price":100,"changePercentage":1.0,"timestamp":1791300000}])
def td(req,timeout):return R({"close":"4155","percent_change":"0.3","timestamp":1791230400})
def oil(req,timeout):return R({"quoteType":"intraday","quoteStatus":"current","provider":"Yahoo Finance (CL=F)","dataSource":"Yahoo Finance (CL=F)","priceUsd":87.26,"changePct":-2.43,"observedAt":"2026-10-06T13:02:49Z"})
def test_resolved_five_routes_and_missing_two():
    r=build_resolved_five_observational_router(fmp_api_key="f",twelvedata_api_key="t",fmp_opener=fmp,twelvedata_opener=td,oil_opener=oil)
    s=r.snapshot()
    assert s["configured_assets"]==("US500","NASDAQ","VIX","OIL","GOLD")
    assert s["missing_assets"]==("DXY","US10Y")
    assert s["complete"] is False
    for a in s["configured_assets"]:
        x=r.fetch(a);assert x and x["internal_asset"]==a
    assert r.fetch("DXY") is None and r.fetch("US10Y") is None
def test_static_snapshot_is_fail_closed():
    s=snapshot()
    assert s["complete"] is False
    assert s["observational_only"] is True
    assert s["operational_influence_allowed"] is False
    assert s["automatic_activation"] is False
    assert s["environment_reads"] is False
