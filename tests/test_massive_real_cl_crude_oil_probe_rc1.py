"""Offline tests for Massive CL crude-oil probe RC1."""
import json, pytest
from tools.massive_real_cl_crude_oil_probe_rc1 import run

class R:
    def __init__(self,p): self.b=json.dumps(p).encode()
    def read(self): return self.b

def test_key_required():
    with pytest.raises(ValueError,match="MASSIVE_API_KEY"): run("")

def test_cl_evidence_without_expiry_selection_or_promotion():
    def opener(req,timeout):
        if "/products?" in req.full_url:
            return R({"results":[{"product_code":"CL","name":"Crude Oil Futures","asset_class":"commodity","asset_sub_class":"energy","trading_venue":"XNYM","unit_of_measure":"BBL"}]})
        return R({"results":[{"ticker":"CLX6","product_code":"CL","active":True,"last_trade_date":"2026-10-20","trading_venue":"XNYM"}]})
    x=run("secret",opener)
    assert x["product"]["rows"][0]["product_code"]=="CL"
    assert x["active_contracts"]["rows"][0]["ticker"]=="CLX6"
    assert x["candidate_is_approved_mapping"] is False
    assert x["selects_futures_expiry"] is False
    assert x["creates_router_route"] is False
    assert "secret" not in json.dumps(x)

def test_empty_results_fail_closed():
    x=run("key",lambda req,timeout:R({"results":[]}))
    assert x["product"]["rows"]==[]
    assert x["active_contracts"]["rows"]==[]
