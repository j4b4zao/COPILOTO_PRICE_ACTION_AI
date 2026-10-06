"""Offline contract tests for Massive WTI product evidence probe RC1."""
import json
import pytest
from tools.massive_real_wti_product_probe_rc1 import run

class Response:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8")
    def read(self):
        return self.raw

def test_requires_explicit_key():
    with pytest.raises(ValueError, match="MASSIVE_API_KEY"):
        run("")

def test_reports_wti_without_promotion():
    def opener(request, timeout):
        return Response({"results":[{"product_code":"WTI","name":"WTI Crude Oil","exchange":"EXAMPLE","asset_class":"Energy"}]})
    result = run("secret", opener=opener)
    assert result["request_status"] == "OK"
    assert result["matches"][0]["product_code"] == "WTI"
    assert result["candidate_alias_is_approved_mapping"] is False
    assert result["creates_router_route"] is False
    assert result["selects_futures_expiry"] is False
    assert "secret" not in json.dumps(result)

def test_non_wti_rows_fail_closed():
    result = run("key", opener=lambda request, timeout: Response({"results":[{"product_code":"BRENT","name":"Brent"}]}))
    assert result["matches"] == []
