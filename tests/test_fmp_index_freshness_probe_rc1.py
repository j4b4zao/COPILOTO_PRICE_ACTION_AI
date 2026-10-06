from __future__ import annotations

import json
from io import BytesIO

import pytest

from tools.fmp_index_freshness_probe_rc1 import run


class _Response:
    def __init__(self, payload):
        self._payload = payload
    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _opener(request, timeout):
    symbol = request.full_url.split("symbol=")[1].split("&")[0]
    symbol = symbol.replace("%5E", "^")
    timestamps = {
        "^GSPC": 1791316800,
        "^IXIC": 1791311400,
        "^VIX": 1791321000,
    }
    return _Response([{
        "symbol": symbol,
        "price": 100.0,
        "changePercentage": 1.0,
        "timestamp": timestamps[symbol],
    }])


def test_probe_classifies_fresh_stale_and_future():
    result = run(
        enabled=True,
        reference_timestamp="2026-10-06T20:00:00+00:00",
        maximum_staleness_seconds=3600,
        fmp_api_key="test",
        opener=_opener,
    )
    rows = {row["symbol"]: row for row in result["rows"]}
    assert result["diagnostic_only"] is True
    assert result["operational_influence_allowed"] is False
    assert rows["^GSPC"]["status"] == "FRESH"
    assert rows["^IXIC"]["status"] == "STALE"
    assert rows["^VIX"]["status"] == "FUTURE"


def test_probe_requires_explicit_enable():
    with pytest.raises(PermissionError):
        run(
            enabled=False,
            reference_timestamp="2026-10-06T20:00:00+00:00",
            maximum_staleness_seconds=3600,
            fmp_api_key="test",
            opener=_opener,
        )


@pytest.mark.parametrize("timestamp", ["2026-10-06T20:00:00", "not-a-time"])
def test_probe_rejects_invalid_reference_timestamp(timestamp):
    with pytest.raises(ValueError):
        run(
            enabled=True,
            reference_timestamp=timestamp,
            maximum_staleness_seconds=3600,
            fmp_api_key="test",
            opener=_opener,
        )


def test_probe_rejects_nonpositive_threshold():
    with pytest.raises(ValueError):
        run(
            enabled=True,
            reference_timestamp="2026-10-06T20:00:00+00:00",
            maximum_staleness_seconds=0,
            fmp_api_key="test",
            opener=_opener,
        )
