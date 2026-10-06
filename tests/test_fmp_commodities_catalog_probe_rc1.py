import json

import pytest

from tools.fmp_commodities_catalog_probe_rc1 import run


class R:
    def __init__(self, payload):
        self.payload = payload
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_requires_key():
    with pytest.raises(ValueError):
        run("")


def test_discovers_oil_rows_without_promoting_mapping():
    rows = [
        {"symbol":"CLUSD","name":"Crude Oil WTI","exchange":"COMMODITY","tradeMonth":"December"},
        {"symbol":"GCUSD","name":"Gold","exchange":"COMMODITY"},
        {"symbol":"BZUSD","name":"Brent Crude Oil","exchange":"COMMODITY"},
    ]
    x = run("secret", opener=lambda req, timeout: R(rows))
    assert x["catalog_status"] == "OK"
    assert x["catalog_row_count"] == 3
    assert x["oil_like_row_count"] == 2
    assert [r["symbol"] for r in x["oil_like_rows"]] == ["CLUSD","BZUSD"]
    assert x["oil_candidate_is_approved_mapping"] is False
    assert x["creates_provider_symbol_map"] is False
    assert x["creates_manifest"] is False
    assert x["creates_router_route"] is False
    assert "secret" not in json.dumps(x)


def test_empty_catalog_is_valid_but_finds_no_oil():
    x = run("key", opener=lambda req, timeout: R([]))
    assert x["catalog_status"] == "OK"
    assert x["catalog_row_count"] == 0
    assert x["oil_like_rows"] == []
