from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from tools.fmp_quote_vs_intraday_1min_probe_rc1 import run


class _Response:
    def __init__(self, payload):
        self.payload = payload
    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _symbol(request):
    return parse_qs(urlparse(request.full_url).query)["symbol"][0]


def _quote_opener(request, timeout):
    symbol = _symbol(request)
    return _Response([{
        "symbol": symbol,
        "price": 100.0,
        "changePercentage": 1.0,
        "timestamp": 1791313200,
    }])


def _intraday_aware(request, timeout):
    return _Response([{
        "date": "2026-10-06T19:59:00+00:00",
        "open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0, "volume": 1,
    }])


def _intraday_naive(request, timeout):
    return _Response([{
        "date": "2026-10-06 15:59:00",
        "open": 99.0, "high": 101.0, "low": 98.0, "close": 100.0, "volume": 1,
    }])


def test_comparator_classifies_aware_quote_and_minute_independently():
    result = run(
        enabled=True,
        reference_timestamp="2026-10-06T20:00:00+00:00",
        maximum_staleness_seconds=3600,
        fmp_api_key="test",
        quote_opener=_quote_opener,
        intraday_opener=_intraday_aware,
    )
    assert result["diagnostic_only"] is True
    assert result["operational_influence_allowed"] is False
    assert len(result["rows"]) == 3
    for row in result["rows"]:
        assert row["quote"]["status"] in {"FRESH", "STALE", "FUTURE"}
        assert row["intraday_1min"]["status"] == "FRESH"


def test_comparator_refuses_to_guess_naive_intraday_timezone():
    result = run(
        enabled=True,
        reference_timestamp="2026-10-06T20:00:00+00:00",
        maximum_staleness_seconds=3600,
        fmp_api_key="test",
        quote_opener=_quote_opener,
        intraday_opener=_intraday_naive,
    )
    for row in result["rows"]:
        minute = row["intraday_1min"]
        assert minute["timestamp_status"] == "AMBIGUOUS_TIMEZONE"
        assert "age_seconds" not in minute
        assert "status" not in minute


def test_comparator_requires_explicit_enable():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T20:00:00+00:00",
            maximum_staleness_seconds=3600,
            fmp_api_key="test",
        )


@pytest.mark.parametrize("threshold", [0, -1])
def test_comparator_rejects_nonpositive_threshold(threshold):
    with pytest.raises(ValueError):
        run(
            enabled=True,
            reference_timestamp="2026-10-06T20:00:00+00:00",
            maximum_staleness_seconds=threshold,
            fmp_api_key="test",
        )
