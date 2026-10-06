"""Offline acceptance tests for TwelveDataQuoteTransport RC1."""
import json
from urllib.error import URLError

import pytest

from external_context.providers.twelvedata_quote_transport import TwelveDataQuoteTransport


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw


def test_construction_is_inert_and_explicit():
    calls = []
    transport = TwelveDataQuoteTransport(
        api_key="secret",
        opener=lambda *a, **k: calls.append((a, k)),
    )
    assert calls == []
    assert transport.snapshot()["observational_only"] is True


@pytest.mark.parametrize("api_key", ["", " ", None])
def test_api_key_is_required(api_key):
    with pytest.raises(ValueError, match="api_key"):
        TwelveDataQuoteTransport(api_key=api_key)


@pytest.mark.parametrize("timeout", [0, -1])
def test_timeout_must_be_positive(timeout):
    with pytest.raises(ValueError, match="timeout"):
        TwelveDataQuoteTransport(api_key="x", timeout=timeout)


def test_fetch_builds_quote_request_and_normalizes_payload():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return Response({
            "symbol": "SPX",
            "close": "6725.50",
            "percent_change": "0.42",
            "datetime": "2026-10-06",
            "timestamp": 1791300600,
        })

    transport = TwelveDataQuoteTransport(api_key="key value", timeout=3, opener=opener)
    result = transport.fetch("SPX")

    assert "symbol=SPX" in seen["url"]
    assert "apikey=key+value" in seen["url"]
    assert seen["timeout"] == 3
    assert result == {
        "price": 6725.5,
        "change": 0.42,
        "timestamp": "2026-10-06T15:30:00+00:00",
    }


def test_provider_symbol_is_url_encoded():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        return Response({"close": "1", "percent_change": "0", "timestamp": 1791300600})

    TwelveDataQuoteTransport(api_key="x", opener=opener).fetch("WTI/USD")
    assert "symbol=WTI%2FUSD" in seen["url"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"status": "error", "code": 400, "message": "bad symbol"},
        {"close": "bad", "percent_change": "1"},
        {"close": "100"},
        {"close": "0", "percent_change": "1"},
        {"close": "100", "percent_change": "1", "datetime": "2026-10-06"},
        {"close": "100", "percent_change": "1", "timestamp": "bad"},
        [],
    ],
)
def test_invalid_or_provider_error_payload_returns_none(payload):
    transport = TwelveDataQuoteTransport(
        api_key="x",
        opener=lambda *a, **k: Response(payload),
    )
    assert transport.fetch("SPX") is None


def test_network_error_returns_none():
    def opener(*args, **kwargs):
        raise URLError("offline")

    transport = TwelveDataQuoteTransport(api_key="x", opener=opener)
    assert transport.fetch("SPX") is None


def test_empty_provider_symbol_fails_before_opener():
    calls = []
    transport = TwelveDataQuoteTransport(
        api_key="x",
        opener=lambda *a, **k: calls.append(1),
    )

    with pytest.raises(ValueError, match="provider_symbol"):
        transport.fetch(" ")

    assert calls == []


def test_snapshot_never_exposes_api_key():
    transport = TwelveDataQuoteTransport(api_key="TOP-SECRET")
    snapshot = transport.snapshot()

    assert "TOP-SECRET" not in repr(snapshot)
    assert set(snapshot) == {
        "name", "version", "base_url", "timeout", "configured", "observational_only",
        "timestamp_semantics"
    }
    assert snapshot["timestamp_semantics"] == "provider_unix_seconds_to_utc_iso8601"


def test_unix_timestamp_takes_precedence_over_date_only_datetime():
    transport = TwelveDataQuoteTransport(
        api_key="x",
        opener=lambda *a, **k: Response({
            "close": "4155.94217",
            "percent_change": "0.35972798",
            "datetime": "2026-10-06",
            "timestamp": 1791230400,
        }),
    )
    result = transport.fetch("XAU/USD")
    assert result["timestamp"] == "2026-10-06T00:00:00+00:00"
