"""Explicit synthetic observations, never market-performance evidence."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import ast

import pytest
from replay.historical_rtd_capture import (
    RTDObservation, RTDCaptureValidationError, HistoricalRTDCapture, SCHEMA,
)

T = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)


def obs(kind="SESSION_START", n=0, **kwargs):
    return RTDObservation(**dict(session_id="synthetic-session", symbol=" winv26 ",
        source_id=" synthetic_source ", observed_at=T+timedelta(seconds=n),
        captured_at=T+timedelta(seconds=n, microseconds=1), observation_type=kind,
        payload={"fixture": True}) | kwargs)


def start(path):
    HistoricalRTDCapture.append(path, obs())


def test_deep_immutability():
    raw = {"rows": [{"quantity": 2}], "unknown": None}
    value = obs(payload=raw)
    raw["rows"][0]["quantity"] = 7
    assert value.payload["rows"][0]["quantity"] == 2
    with pytest.raises(TypeError):
        value.payload["rows"][0]["quantity"] = 3
    with pytest.raises(FrozenInstanceError):
        value.symbol = "OTHER"


@pytest.mark.parametrize("changes", [
    {"source_id": ""}, {"source_id": "UNKNOWN"}, {"session_id": ""}, {"symbol": ""},
    {"observed_at": None}, {"captured_at": "2026-10-08"},
    {"observed_at": T.replace(tzinfo=None)}, {"captured_at": T-timedelta(seconds=1)},
    {"source_event_at": T+timedelta(seconds=1)},
    {"source_event_at": T.replace(tzinfo=None)}, {"observation_type": "TRADE"},
    {"integrity_status": "COMPLETE"}, {"payload": []}, {"payload": {1: "bad"}},
    {"payload": {"x": float("nan")}}, {"payload": {"x": float("inf")}},
    {"payload": {"x": object()}}, {"payload": {"x": {1, 2}}},
])
def test_invalid_contract(changes):
    with pytest.raises(RTDCaptureValidationError):
        obs(**changes)


def test_json_roundtrip_preserves_observations(tmp_path):
    path = tmp_path/"capture.jsonl"
    with HistoricalRTDCapture.open_writer(path, anchor_path=tmp_path/"anchor.jsonl",
                                          anchor_key=b"SYNTHETIC_TEST_KEY_ONLY_32_BYTES!!") as writer:
        writer.append(obs())
        writer.append(obs("TIMES_TRADES_SNAPSHOT", 1,
            payload={"rows": [{"quantity": 2, "aggressor": "UNKNOWN"}]}))
    result = HistoricalRTDCapture.recover(path)
    assert result.clean and len(result.observations) == 2
    assert result.last_observation.payload["rows"][0]["aggressor"] == "UNKNOWN"
    assert "event_id" not in result.last_observation.payload["rows"][0]
    assert "delta" not in result.last_observation.payload
    assert result.current_snapshots == ()  # Reopening cannot certify freshness.


def test_legacy_append_requires_explicit_writer(tmp_path):
    with pytest.raises(RTDCaptureValidationError, match="EXCLUSIVE_ANCHORED_WRITER_REQUIRED"):
        HistoricalRTDCapture.append(tmp_path/"capture.jsonl", obs())
    assert not (tmp_path/"capture.jsonl").exists()


def test_no_live_or_operational_imports_or_clock():
    source = Path("replay/historical_rtd_capture.py").read_text(encoding="utf-8")
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append(node.module)
    assert not any(name.startswith(("market_data", "analysis", "core", "requests",
                                   "socket", "win32", "xlwings")) for name in modules)
    assert "datetime.now" not in source and "datetime.today" not in source
