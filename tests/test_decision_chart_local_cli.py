"""Local chart export entry point acceptance tests."""

from dataclasses import asdict
import json
from xml.etree import ElementTree as ET

import pytest

from app.decision_chart_local_cli import run
from dashboard.copilot_readonly_dashboard import project
from tests.test_copilot_readonly_dashboard_rc1 import prepared


def payload():
    return {
        "candles": [
            {"open": 10, "high": 12, "low": 9, "close": 11},
            {"open": 11, "high": 13, "low": 10, "close": 12},
        ],
        "decision": asdict(project(prepared()).decision),
        "marker_index": 1,
    }


def test_export_renders_supplied_snapshot_and_preserves_input(tmp_path):
    source = tmp_path / "input.json"
    target = tmp_path / "chart.svg"
    raw = json.dumps(payload()).encode("utf-8-sig")
    source.write_bytes(raw)
    assert run(["--file", str(source), "--output", str(target)]) == 0
    root = ET.fromstring(target.read_text(encoding="utf-8"))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.find("s:g/s:polygon", ns) is not None
    assert "OFFICIAL DECISION BUY" in root.find("s:g/s:title", ns).text
    assert source.read_bytes() == raw


def test_existing_output_is_preserved(tmp_path):
    source = tmp_path / "input.json"
    source.write_text(json.dumps(payload()), encoding="utf-8")
    target = tmp_path / "chart.svg"
    target.write_bytes(b"preserved")
    assert run(["--file", str(source), "--output", str(target)]) == 2
    assert target.read_bytes() == b"preserved"


@pytest.mark.parametrize("mutation", [
    lambda data: data.update(marker_index=-1),
    lambda data: data.update(marker_index=True),
    lambda data: data.update(candles=[]),
    lambda data: data.update(decision={}),
    lambda data: data["candles"][0].update(high=float("nan")),
])
def test_invalid_input_does_not_create_output(tmp_path, mutation):
    data = payload()
    mutation(data)
    source = tmp_path / "input.json"
    source.write_text(json.dumps(data), encoding="utf-8")
    target = tmp_path / "chart.svg"
    assert run(["--file", str(source), "--output", str(target)]) == 2
    assert not target.exists()


def test_missing_source_does_not_create_output(tmp_path):
    target = tmp_path / "chart.svg"
    assert run(["--file", str(tmp_path / "missing.json"), "--output", str(target)]) == 2
    assert not target.exists()

