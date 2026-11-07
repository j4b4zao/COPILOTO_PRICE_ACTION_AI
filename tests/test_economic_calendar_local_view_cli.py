"""Acceptance tests for manual calendar display with local input."""

import json
from pathlib import Path

import pytest

from app.economic_calendar_local_view_cli import run


ARGS = ["--symbol", "WINV26", "--now", "2026-11-07T12:00:00+00:00"]
EVENT = {
    "title": "Local release",
    "scheduled_at": "2026-11-07T12:05:00+00:00",
    "impact": "HIGH",
    "currency": "USD",
    "country": "US",
}


def output(capsys):
    return json.loads(capsys.readouterr().out.split("\n", 1)[1])


def test_valid_file_is_displayed_without_modification(tmp_path, capsys):
    path = tmp_path / "events.json"
    original = json.dumps([EVENT]).encode("utf-8-sig")
    path.write_bytes(original)
    assert run(["--file", str(path), *ARGS]) == 0
    state = output(capsys)
    assert state["status"] == "HIGH_IMPACT_WINDOW"
    assert state["next_event"]["title"] == EVENT["title"]
    assert state["source"] == "LOCAL_FILE"
    assert state["observed_at"] == "2026-11-07T12:00:00+00:00"
    assert state["observational_only"] is True
    assert path.read_bytes() == original


def test_empty_calendar_is_available(tmp_path, capsys):
    path = tmp_path / "events.json"
    path.write_text("[]", encoding="utf-8")
    assert run(["--file", str(path), *ARGS]) == 0
    assert output(capsys)["status"] == "NO_EVENTS"


@pytest.mark.parametrize("data", ["{", '[{"title":"invalid"}]', json.dumps([EVENT, {}])])
def test_invalid_payload_is_explicitly_unavailable(tmp_path, capsys, data):
    path = tmp_path / "events.json"
    path.write_text(data, encoding="utf-8")
    assert run(["--file", str(path), *ARGS]) == 2
    state = output(capsys)
    assert state["status"] == "UNAVAILABLE"
    assert state["events"] == []
    assert state["observational_only"] is True


def test_missing_file_is_not_created(tmp_path, capsys):
    path = tmp_path / "missing.json"
    assert run(["--file", str(path), *ARGS]) == 2
    assert output(capsys)["status"] == "UNAVAILABLE"
    assert not path.exists()


@pytest.mark.parametrize("stamp", ["2026-11-07T12:00:00", "invalid"])
def test_invalid_reference_time_fails_before_file_read(monkeypatch, stamp):
    def fail(*args, **kwargs):
        raise AssertionError("Input file should not be read")
    monkeypatch.setattr(Path, "read_text", fail)
    with pytest.raises(SystemExit) as error:
        run(["--file", "unused.json", "--symbol", "WINV26", "--now", stamp])
    assert error.value.code == 2

