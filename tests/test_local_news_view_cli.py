"""Acceptance tests for the manual local headline entry point."""

import json
from pathlib import Path

import pytest

from app.local_news_view_cli import run


ARGS = ["--now", "2026-11-09T12:00:00+00:00", "--max-age-minutes", "10"]
ROW = dict(id="1", title="Synthetic local headline", source="LOCAL",
           published_at="2026-11-09T11:55:00+00:00")


def data(capsys):
    return json.loads(capsys.readouterr().out.split("\n", 1)[1])


def test_valid_file_is_displayed_and_preserved(tmp_path, capsys):
    path = tmp_path / "news.json"
    raw = json.dumps([ROW]).encode("utf-8-sig")
    path.write_bytes(raw)
    assert run(["--file", str(path), *ARGS]) == 0
    result = data(capsys)
    assert result["status"] == "READY"
    assert result["headlines"][0]["title"] == ROW["title"]
    assert result["headlines"][0]["freshness"] == "FRESH"
    assert result["observational_only"] is True
    assert path.read_bytes() == raw


@pytest.mark.parametrize("payload", ["{", "{}", '[{"title":"partial"}]'])
def test_invalid_file_is_explicitly_unavailable(tmp_path, capsys, payload):
    path = tmp_path / "news.json"
    path.write_text(payload, encoding="utf-8")
    assert run(["--file", str(path), *ARGS]) == 2
    result = data(capsys)
    assert result["status"] == "UNAVAILABLE"
    assert result["headlines"] == []


def test_missing_file_is_not_created(tmp_path, capsys):
    path = tmp_path / "missing.json"
    assert run(["--file", str(path), *ARGS]) == 2
    assert data(capsys)["status"] == "UNAVAILABLE"
    assert not path.exists()


def test_empty_file_list_is_available(tmp_path, capsys):
    path = tmp_path / "news.json"
    path.write_text("[]", encoding="utf-8")
    assert run(["--file", str(path), *ARGS]) == 0
    assert data(capsys)["status"] == "NO_NEWS"


@pytest.mark.parametrize("now,age", [
    ("2026-11-09T12:00:00", "10"),
    ("2026-11-09T12:00:00+00:00", "0"),
    ("2026-11-09T12:00:00+00:00", "nan"),
    ("2026-11-09T12:00:00+00:00", "inf"),
    ("2026-11-09T12:00:00+00:00", "1e300"),
])
def test_invalid_reference_policy_fails_before_read(monkeypatch, now, age):
    def fail(*args, **kwargs):
        raise AssertionError("Unexpected file read")
    monkeypatch.setattr(Path, "read_text", fail)
    with pytest.raises(SystemExit) as error:
        run(["--file", "unused.json", "--now", now, "--max-age-minutes", age])
    assert error.value.code == 2

