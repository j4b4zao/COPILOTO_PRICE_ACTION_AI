import json
from urllib.parse import parse_qs, urlparse

import pytest

from tools.massive_real_clf7_quote_probe_rc1 import run


class R:
    def __init__(self, payload):
        self.payload = payload
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_blank_key_rejected():
    with pytest.raises(ValueError):
        run("")


def test_quote_is_observational_and_timestamp_is_utc_iso():
    seen = {}
    def opener(req, timeout):
        seen["url"] = req.full_url
        return R({"status": "OK", "results": [{
            "ticker": "CLF7",
            "bid_price": 61.25,
            "ask_price": 61.26,
            "bid_size": 10,
            "ask_size": 12,
            "session_end_date": "2026-10-06",
            "timestamp": 1791305940123456789,
        }]})
    x = run("secret-key", opener=opener)
    assert x["observational_only"] is True
    assert x["candidate_is_approved_mapping"] is False
    assert x["creates_provider_symbol_map"] is False
    assert x["creates_manifest"] is False
    assert x["creates_router_route"] is False
    assert x["selects_futures_expiry"] is False
    assert x["quote"]["ticker"] == "CLF7"
    assert x["quote"]["timestamp_ns"] == 1791305940123456789
    assert x["quote"]["timestamp_utc_iso"].endswith("+00:00")
    assert x["timestamp_semantics"] == "provider_unix_nanoseconds_to_utc_iso8601"
    assert "secret-key" not in json.dumps(x)
    qs = parse_qs(urlparse(seen["url"]).query)
    assert qs["limit"] == ["1"]
    assert qs["sort"] == ["timestamp.desc"]


def test_empty_results_fail_closed_without_inventing_quote():
    x = run("key", opener=lambda req, timeout: R({"status": "OK", "results": []}))
    assert x["request_status"] == "OK"
    assert x["row_count"] == 0
    assert x["quote"] == {}


def test_invalid_timestamp_does_not_gain_timezone_semantics():
    x = run("key", opener=lambda req, timeout: R({"status": "OK", "results": [
        {"ticker": "CLF7", "timestamp": "not-a-timestamp"}
    ]}))
    assert x["quote"]["timestamp_utc_iso"] is None
