"""Local news presentation and Bot activation acceptance coverage."""

from contextlib import redirect_stdout
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
import json
import pickle
from unittest.mock import patch

import pytest

from app.bot import Bot
from dashboard.local_news_readonly_dashboard import render_local_news
from economic_context.local_news import evaluate_local_news
from tests.test_copilot_readonly_dashboard_rc1 import prepared, guard_side_effects


NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


def state():
    return evaluate_local_news([
        dict(id="1", source="LOCAL", title='<tag>"\\nReported',
             published_at="2026-11-09T11:55:00+00:00"),
        dict(id="2", source="LOCAL", title="Old",
             published_at="2026-11-09T11:00:00+00:00"),
        dict(id="3", source="LOCAL", title="Future",
             published_at="2026-11-09T12:05:00+00:00"),
    ], now=NOW, max_age=timedelta(minutes=10))


def test_presentation_preserves_reported_fields_and_is_pure(monkeypatch):
    supplied = state()
    before = pickle.dumps(supplied)
    with monkeypatch.context() as guarded:
        spies = guard_side_effects(guarded)
        first = render_local_news(supplied)
        second = render_local_news(supplied)
        assert all(spy.call_count == 0 for spy in spies)
    assert first == second
    assert pickle.dumps(supplied) == before
    data = json.loads(first.split("\n", 1)[1])
    assert data["observed_at"] == supplied.observed_at
    assert [(r["title"], r["freshness"]) for r in data["headlines"]] == [
        (h.title, h.freshness) for h in supplied.headlines
    ]


def test_missing_and_invalid_batches_are_explicit():
    assert render_local_news(None).endswith("NEWS DATA UNAVAILABLE")
    unavailable = evaluate_local_news([{}], now=NOW, max_age=timedelta(minutes=10))
    data = json.loads(render_local_news(unavailable).split("\n", 1)[1])
    assert data["status"] == "UNAVAILABLE"
    assert data["reasons"] == ["INVALID_PAYLOAD"]


@pytest.mark.parametrize("invalid", [False, {}, "news", 1])
def test_wrong_envelopes_are_rejected(invalid):
    with pytest.raises(TypeError):
        render_local_news(invalid)


def test_nonobservational_state_is_rejected():
    with pytest.raises(ValueError):
        render_local_news(replace(state(), observational_only=False))


@pytest.mark.parametrize("enabled", [False, True, 1, None])
def test_bot_activation_is_explicit_and_context_unchanged(enabled):
    context = prepared()
    supplied = state()
    before = pickle.dumps((context, supplied))
    output = io.StringIO()
    with patch("app.bot.render_local_news", wraps=render_local_news) as renderer:
        with redirect_stdout(output):
            object.__new__(Bot).mostrar(
                context, news_state=supplied, news_presentation_enabled=enabled
            )
    assert renderer.call_count == int(enabled is True)
    assert pickle.dumps((context, supplied)) == before
    assert "OFFICIAL DECISION: BUY" in output.getvalue()
    if enabled is False:
        assert "LOCAL NEWS" not in output.getvalue()
    elif enabled is True:
        assert '"freshness": "STALE"' in output.getvalue()
        assert '"freshness": "FUTURE"' in output.getvalue()
    else:
        assert "LOCAL NEWS OBSERVATIONAL UNAVAILABLE" in output.getvalue()


def test_news_failure_keeps_other_optional_presentations():
    context = prepared()
    before = pickle.dumps(context)
    output = io.StringIO()
    with patch("app.bot.render_local_news", side_effect=ValueError("synthetic")):
        with redirect_stdout(output):
            object.__new__(Bot).mostrar(
                context, news_presentation_enabled=True,
                calendar_presentation_enabled=True, external_presentation_enabled=True,
            )
    text = output.getvalue()
    assert "LOCAL NEWS OBSERVATIONAL UNAVAILABLE" in text
    assert "ECONOMIC CALENDAR OBSERVATIONAL" in text
    assert "EXTERNAL OBSERVATIONAL DATA UNAVAILABLE" in text
    assert "OFFICIAL DECISION: BUY" in text
    assert pickle.dumps(context) == before

