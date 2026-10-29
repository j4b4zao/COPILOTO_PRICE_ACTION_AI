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


def _run_intraday(opener, **kwargs):
    return run(enabled=True, reference_timestamp="2026-10-06T20:00:00+00:00",
               maximum_staleness_seconds=3600, fmp_api_key="test",
               quote_opener=_quote_opener, intraday_opener=opener, **kwargs)


@pytest.mark.parametrize("reverse", [False, True])
def test_latest_bar_is_selected_by_absolute_timestamp(reverse):
    bars = [{"date": "2026-10-06T19:59:00Z", "close": 100},
            {"date": "2026-10-06T17:00:00-03:00", "close": 101}]
    if reverse:
        bars.reverse()
    result = _run_intraday(lambda *a, **k: _Response(bars))
    for row in result["rows"]:
        assert row["intraday_1min"]["close"] == 101
        assert row["intraday_1min"]["age_seconds"] == 0


def test_request_encodes_each_index_and_api_key():
    seen = []
    def opener(request, timeout):
        assert urlparse(request.full_url).path == "/stable/historical-chart/1min"
        assert "symbol=%5E" in request.full_url
        assert timeout == 5.0
        seen.append(_symbol(request))
        return _intraday_aware(request, timeout)
    _run_intraday(opener)
    assert seen == ["^GSPC", "^IXIC", "^VIX"]


@pytest.mark.parametrize("payload,status", [
    ({"Error Message": "restricted"}, "INVALID_PAYLOAD"),
    ([], "EMPTY_PAYLOAD"), ([None], "INVALID_PAYLOAD"),
    ([{"date": "bad", "close": 1}], "INVALID_PAYLOAD"),
    ([{"date": "2026-10-06T20:00:00Z"}], "INVALID_PAYLOAD"),
    ([{"date": "2026-10-06T20:00:00Z", "close": float("nan")}], "INVALID_PAYLOAD"),
    ([{"date": "2026-10-06T20:00:00Z", "close": float("inf")}], "INVALID_PAYLOAD"),
    ([{"date": "2026-10-06T20:00:00Z", "close": True}], "INVALID_PAYLOAD"),
])
def test_bad_payloads_remain_fail_closed(payload, status):
    for row in _run_intraday(lambda *a, **k: _Response(payload))["rows"]:
        assert row["intraday_1min"] == {"status": status}
        assert row["quote"] is not None


def test_mixed_timezone_payload_is_ambiguous():
    payload = [{"date": "2026-10-06T20:00:00Z", "close": 1},
               {"date": "2026-10-06 16:00:00", "close": 2}]
    for row in _run_intraday(lambda *a, **k: _Response(payload))["rows"]:
        assert row["intraday_1min"] == {"timestamp_status": "AMBIGUOUS_TIMEZONE"}


@pytest.mark.parametrize("kind,status", [("http", "HTTP_ERROR"), ("network", "TRANSPORT_ERROR"),
                                          ("timeout", "TRANSPORT_ERROR"), ("json", "INVALID_JSON")])
def test_fetch_errors_are_diagnostic_and_do_not_expose_secrets(kind, status):
    from urllib.error import HTTPError, URLError
    def opener(*args, **kwargs):
        if kind == "http":
            raise HTTPError("https://example/?apikey=SECRET", 403, "SECRET", {}, None)
        if kind == "network":
            raise URLError("SECRET")
        if kind == "timeout":
            raise TimeoutError("SECRET")
        class BadResponse:
            def read(self):
                return b"not json"
        return BadResponse()
    result = _run_intraday(opener)
    assert "SECRET" not in repr(result)
    for row in result["rows"]:
        assert row["intraday_1min"]["status"] == status


@pytest.mark.parametrize("threshold", [float("nan"), float("inf")])
def test_nonfinite_threshold_is_rejected(threshold):
    with pytest.raises(ValueError):
        run(enabled=True, reference_timestamp="2026-10-06T20:00:00Z",
            maximum_staleness_seconds=threshold, fmp_api_key="test")


@pytest.mark.parametrize("timestamp", ["bad", "2026-10-06T20:00:00"])
def test_comparator_rejects_invalid_reference_before_network(timestamp):
    with pytest.raises(ValueError):
        run(enabled=True, reference_timestamp=timestamp,
            maximum_staleness_seconds=3600, fmp_api_key="test")


@pytest.mark.parametrize("quote_state", ["FUTURE", "STALE", "UNAVAILABLE"])
@pytest.mark.parametrize("intraday_state", ["FRESH", "HTTP_402"])
def test_intraday_never_replaces_unusable_quote(quote_state, intraday_state):
    from datetime import datetime, timedelta
    from urllib.error import HTTPError

    reference = datetime.fromisoformat("2026-10-07T13:56:25+00:00")
    calls = []

    def quote(request, timeout):
        calls.append(("quote", _symbol(request)))
        if quote_state == "UNAVAILABLE":
            return _Response([])
        age = -1 if quote_state == "FUTURE" else 3601
        return _Response([{"symbol": _symbol(request), "price": 100,
                           "changePercentage": 1,
                           "timestamp": (reference - timedelta(seconds=age)).timestamp()}])

    def minute(request, timeout):
        calls.append(("minute", _symbol(request)))
        if intraday_state == "HTTP_402":
            raise HTTPError(request.full_url, 402, "restricted", {}, None)
        return _Response([{"date": reference.isoformat(), "close": 999}])

    result = run(enabled=True, reference_timestamp=reference.isoformat(),
                 maximum_staleness_seconds=3600, fmp_api_key="offline",
                 quote_opener=quote, intraday_opener=minute)
    assert calls == [(source, symbol) for symbol in ("^GSPC", "^IXIC", "^VIX")
                     for source in ("quote", "minute")]
    assert result["operational_influence_allowed"] is False
    for row in result["rows"]:
        assert set(row) == {"symbol", "quote", "intraday_1min"}
        if quote_state == "UNAVAILABLE":
            assert row["quote"] is None
        else:
            assert row["quote"]["status"] == quote_state
            assert row["quote"]["price"] == 100
        if intraday_state == "HTTP_402":
            assert row["intraday_1min"] == {"status": "HTTP_ERROR", "http_status": 402}
        else:
            assert row["intraday_1min"]["status"] == "FRESH"
            assert row["intraday_1min"]["close"] == 999
