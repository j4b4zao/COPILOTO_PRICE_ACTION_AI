"""Offline tests for Massive CL crude-oil probe RC1."""
import json, pytest
from tools.massive_real_cl_crude_oil_probe_rc1 import run

class R:
    def __init__(self,p): self.b=json.dumps(p).encode()
    def read(self): return self.b

def test_key_required():
    with pytest.raises(ValueError,match="MASSIVE_API_KEY"): run("", "2026-10-06")

def test_cl_evidence_without_expiry_selection_or_promotion():
    def opener(req,timeout):
        if "/products?" in req.full_url:
            return R({"results":[{"product_code":"CL","name":"Crude Oil Futures","asset_class":"commodity","asset_sub_class":"energy","trading_venue":"XNYM","unit_of_measure":"BBL"}]})
        return R({"results":[{"ticker":"CLX6","product_code":"CL","active":True,"last_trade_date":"2026-10-20","trading_venue":"XNYM"}]})
    x=run("secret","2026-10-06",opener)
    assert x["product"]["rows"][0]["product_code"]=="CL"
    assert x["active_contracts"]["rows"][0]["ticker"]=="CLX6"
    assert x["candidate_is_approved_mapping"] is False
    assert x["selects_futures_expiry"] is False
    assert x["creates_router_route"] is False
    assert "secret" not in json.dumps(x)

def test_empty_results_fail_closed():
    x=run("key","2026-10-06",lambda req,timeout:R({"results":[]}))
    assert x["product"]["rows"]==[]
    assert x["active_contracts"]["rows"]==[]


def test_reference_date_required_and_contract_query_sorted_by_maturity():
    with pytest.raises(ValueError,match="reference_date"):
        run("key","")
    seen=[]
    def opener(req,timeout):
        seen.append(req.full_url)
        return R({"results":[]})
    run("key","2026-10-06",opener)
    contract_url=next(u for u in seen if "/contracts?" in u)
    assert "date=2026-10-06" in contract_url
    assert "active=true" in contract_url
    assert "type=single" in contract_url
    assert "sort=days_to_maturity.asc" in contract_url
