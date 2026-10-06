import json
import pytest
from tools.fmp_real_clusd_quote_probe_rc1 import run

class R:
    def __init__(self,p): self.p=p
    def read(self): return json.dumps(self.p).encode()

def test_requires_key():
    with pytest.raises(ValueError): run("")

def test_real_shape_validates_price_and_utc_timestamp_without_promotion():
    x=run("secret", opener=lambda req,timeout:R([{
        "symbol":"CLUSD","name":"Crude Oil","price":61.25,
        "change":0.5,"changePercentage":0.82,"timestamp":1791305940,
        "exchange":"COMMODITY"
    }]))
    assert x["quote_evidence_valid"] is True
    assert x["provider_symbol"]=="CLUSD"
    assert x["candidate_is_approved_mapping"] is False
    assert x["creates_provider_symbol_map"] is False
    assert x["creates_manifest"] is False
    assert x["creates_router_route"] is False
    assert x["quote"]["timestamp_utc_iso"].endswith("+00:00")
    assert "secret" not in json.dumps(x)

def test_wrong_symbol_fails_closed():
    x=run("k", opener=lambda req,timeout:R([{"symbol":"BZUSD","price":60,"timestamp":1791305940}]))
    assert x["quote_evidence_valid"] is False

def test_missing_timestamp_fails_closed():
    x=run("k", opener=lambda req,timeout:R([{"symbol":"CLUSD","price":60}]))
    assert x["quote_evidence_valid"] is False

def test_empty_payload_fails_closed():
    x=run("k", opener=lambda req,timeout:R([]))
    assert x["quote_evidence_valid"] is False
    assert x["quote"]=={}
