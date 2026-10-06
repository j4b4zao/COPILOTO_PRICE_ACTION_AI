import json
from tools.americas_oil_watch_wti_probe_rc1 import run

class R:
    def __init__(self,p): self.p=p
    def read(self): return json.dumps(self.p).encode()

def test_observational_aggregator_never_promotes():
    x=run(opener=lambda req,timeout:R({"price":61.2,"source":"Yahoo Finance"}))
    assert x["request_status"]=="OK"
    assert x["observational_only"] is True
    assert x["aggregator_source"] is True
    assert x["candidate_is_approved_mapping"] is False
    assert x["creates_provider_symbol_map"] is False
    assert x["creates_manifest"] is False
    assert x["creates_router_route"] is False

def test_non_dict_payload_fails_closed():
    x=run(opener=lambda req,timeout:R([]))
    assert x["request_status"]=="ERROR"
    assert x["payload"]=={}
