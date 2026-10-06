from datetime import datetime
import json
from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.resolved_five_observational_configuration import build_resolved_five_observational_router

class R:
    def __init__(self,p):self.p=p
    def read(self):return json.dumps(self.p).encode()
def fmp(req,timeout):
    from urllib.parse import parse_qs,urlparse
    s=parse_qs(urlparse(req.full_url).query)["symbol"][0]
    return R([{"symbol":s,"price":100,"changePercentage":1.0,"timestamp":1791300000}])
def td(req,timeout):return R({"close":"4155","percent_change":"0.3","timestamp":1791300000})
def oil(req,timeout):return R({"quoteType":"intraday","quoteStatus":"current","provider":"Yahoo Finance (CL=F)","dataSource":"Yahoo Finance (CL=F)","priceUsd":87.26,"changePct":-2.43,"observedAt":"2026-10-06T15:20:00Z"})
def router():
    return build_resolved_five_observational_router(fmp_api_key="f",twelvedata_api_key="t",fmp_opener=fmp,twelvedata_opener=td,oil_opener=oil)

def test_five_quotes_cross_collector_but_official_state_fails_closed_without_dxy():
    c=ExternalMarketCollector(provider=router(),preserve_quotes=True)
    state=c.collect()
    assert state.valid is False
    assert state.us500>0 and state.nasdaq>0 and state.vix>0 and state.oil>0 and state.gold>0
    assert state.dxy==0 and state.us10y==0
    assert any("DXY" in reason for reason in state.reasons)
    assert c.observational_snapshot is not None
    q=c.observational_snapshot.to_quotes()
    for a in ("US500","NASDAQ","VIX","OIL","GOLD"):assert q[a] is not None
    assert q["DXY"] is None and q["US10Y"] is None

def test_readiness_explicitly_reports_missing_dxy_and_us10y():
    c=ExternalMarketCollector(provider=router(),preserve_quotes=True);c.collect()
    audit=c.observational_snapshot.audit(reference_timestamp=datetime.fromisoformat("2026-10-06T15:30:00+00:00"),maximum_staleness_seconds=3600)
    assert audit.readiness.status=="DATA_NOT_READY"
    assert set(audit.readiness.missing_assets)=={"DXY"}
    assert set(audit.readiness.available_assets)=={"US500","NASDAQ","VIX"}\n    by_asset={x.canonical_symbol:x for x in audit.assets}\n    assert by_asset["US10Y"].status=="MISSING"\n    assert by_asset["OIL"].status=="AVAILABLE" and by_asset["GOLD"].status=="AVAILABLE"
