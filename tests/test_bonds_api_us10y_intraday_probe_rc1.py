import json,pytest
from tools.bonds_api_us10y_intraday_probe_rc1 import run
class R:
    def __init__(self,p):self.p=p
    def read(self):return json.dumps(self.p).encode()
def test_requires_explicit_key_and_date():
    with pytest.raises(ValueError):run("","2026-10-06")
    with pytest.raises(ValueError):run("k","")
    with pytest.raises(ValueError):run("k","2026-02-30")
def test_valid_shape_is_observational():
    x=run("secret","2026-10-06",opener=lambda req,timeout:R({"data":[{"yield":4.123,"fetched_at":"2026-10-06T15:30:00Z"}]}))
    assert x["valid_observation_count"]==1
    assert x["observations"][0]["timestamp_utc_iso"]=="2026-10-06T15:30:00+00:00"
    assert x["candidate_is_approved_mapping"] is False
    assert x["creates_provider_symbol_map"] is False
    assert x["creates_manifest"] is False
    assert x["creates_router_route"] is False
    assert "secret" not in json.dumps(x)
@pytest.mark.parametrize("row",[{"yield":4.1,"fetched_at":"2026-10-06 15:30:00"},{"yield":None,"fetched_at":"2026-10-06T15:30:00Z"},{"yield":0,"fetched_at":"2026-10-06T15:30:00Z"}])
def test_invalid_observation_fails_closed(row):
    assert run("k","2026-10-06",opener=lambda req,timeout:R({"data":[row]}))["valid_observation_count"]==0
def test_empty_is_not_evidence():
    x=run("k","2026-10-06",opener=lambda req,timeout:R({"data":[]}))
    assert x["row_count"]==0 and x["valid_observation_count"]==0
