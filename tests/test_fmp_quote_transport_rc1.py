"""Offline acceptance tests for FMPQuoteTransport RC1."""
import json
from urllib.error import URLError

import pytest

from external_context.providers.fmp_quote_transport import FMPQuoteTransport


class Response:
    def __init__(self, payload):
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._raw


def test_construction_is_inert_and_explicit():
    calls = []
    transport = FMPQuoteTransport(
        api_key="secret",
        opener=lambda *a, **k: calls.append((a, k)),
    )
    assert calls == []
    assert transport.snapshot()["observational_only"] is True


@pytest.mark.parametrize("api_key", ["", " ", None])
def test_api_key_is_required(api_key):
    with pytest.raises(ValueError, match="api_key"):
        FMPQuoteTransport(api_key=api_key)


@pytest.mark.parametrize("timeout", [0, -1])
def test_timeout_must_be_positive(timeout):
    with pytest.raises(ValueError, match="timeout"):
        FMPQuoteTransport(api_key="x", timeout=timeout)


def test_fetch_builds_request_and_normalizes_quote_with_aware_utc_timestamp():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return Response([{
            "symbol": "^GSPC",
            "name": "S&P 500",
            "price": 7825.5,
            "changePercentage": 0.66311,
            "timestamp": 1791311985,
        }])

    transport = FMPQuoteTransport(api_key="key value", timeout=3, opener=opener)
    result = transport.fetch("^GSPC")

    assert "symbol=%5EGSPC" in seen["url"]
    assert "apikey=key+value" in seen["url"]
    assert seen["timeout"] == 3
    assert result == {
        "price": 7825.5,
        "change": 0.66311,
        "timestamp": "2026-10-06T15:59:45+00:00",
    }


def test_returned_symbol_must_match_requested_symbol():
    transport = FMPQuoteTransport(
        api_key="x",
        opener=lambda *a, **k: Response([{
            "symbol": "^IXIC",
            "price": 1,
            "changePercentage": 0,
            "timestamp": 1791311985,
        }]),
    )
    assert transport.fetch("^GSPC") is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        [{}, {}],
        ["bad"],
        [{"symbol": "^GSPC", "price": "bad", "changePercentage": 1, "timestamp": 1791311985}],
        [{"symbol": "^GSPC", "price": 100, "timestamp": 1791311985}],
        [{"symbol": "^GSPC", "price": 0, "changePercentage": 1, "timestamp": 1791311985}],
        [{"symbol": "^GSPC", "price": 100, "changePercentage": 1, "timestamp": None}],
        [{"symbol": "^GSPC", "price": 100, "changePercentage": 1, "timestamp": 0}],
        [{"symbol": "^GSPC", "price": 100, "changePercentage": 1, "timestamp": True}],
    ],
)
def test_invalid_payload_fails_closed(payload):
    transport = FMPQuoteTransport(
        api_key="x",
        opener=lambda *a, **k: Response(payload),
    )
    assert transport.fetch("^GSPC") is None


def test_network_error_returns_none():
    def opener(*args, **kwargs):
        raise URLError("offline")

    assert FMPQuoteTransport(api_key="x", opener=opener).fetch("^GSPC") is None


def test_empty_provider_symbol_fails_before_opener():
    calls = []
    transport = FMPQuoteTransport(
        api_key="x",
        opener=lambda *a, **k: calls.append(1),
    )
    with pytest.raises(ValueError, match="provider_symbol"):
        transport.fetch(" ")
    assert calls == []


def test_snapshot_never_exposes_api_key_and_declares_timestamp_semantics():
    transport = FMPQuoteTransport(api_key="TOP-SECRET")
    snapshot = transport.snapshot()

    assert "TOP-SECRET" not in repr(snapshot)
    assert snapshot["timestamp_semantics"] == "provider_unix_seconds_to_utc_iso8601"
    assert set(snapshot) == {
        "name", "version", "base_url", "timeout", "configured",
        "timestamp_semantics", "observational_only",
    }
