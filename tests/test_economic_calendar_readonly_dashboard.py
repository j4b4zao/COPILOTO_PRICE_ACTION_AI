"""Offline acceptance coverage for calendar evidence presentation."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import pickle
from unittest.mock import patch

import pytest

from dashboard.economic_calendar_readonly_dashboard import render_calendar
from economic_context.economic_calendar_engine import EconomicCalendarEngine
from economic_context.economic_calendar_state import EconomicCalendarState
from economic_context.economic_event import EconomicEvent
from tests.test_copilot_readonly_dashboard_rc1 import guard_side_effects, prepared


NOW = datetime(2026, 11, 7, 12, tzinfo=timezone.utc)


def state():
    event = EconomicEvent(
        "Payroll\nReported", NOW + timedelta(minutes=5), "HIGH", "USD", "US"
    )
    return EconomicCalendarEngine().evaluate([event], now=NOW)


def payload(text):
    return json.loads(text.split("\n", 1)[1])


def test_reported_events_and_status_are_preserved():
    supplied = state()
    evidence = payload(render_calendar(supplied))
    assert evidence["status"] == supplied.status
    assert evidence["observed_at"] == NOW.isoformat()
    assert evidence["events"][0]["title"] == supplied.events[0].title
    assert evidence["active_events"] == evidence["events"]
    assert evidence["next_event"] == evidence["events"][0]
    assert evidence["minutes_to_next"] == 5.0
    assert evidence["observational_only"] is True


def test_unavailable_and_stale_are_explicit():
    assert render_calendar(None).endswith("CALENDAR DATA UNAVAILABLE")
    supplied = EconomicCalendarState.unavailable(NOW, source="fixture")
    evidence = payload(render_calendar(supplied))
    assert evidence["status"] == "UNAVAILABLE"
    assert evidence["reasons"] == ["CALENDAR_NOT_LOADED"]
    stale = replace(state(), stale=True, reasons=("SOURCE_STALE",))
    evidence = payload(render_calendar(stale))
    assert evidence["stale"] is True
    assert evidence["reasons"] == ["SOURCE_STALE"]
    assert evidence["status"] == stale.status


def test_rendering_is_deterministic_detached_and_does_not_recompute(monkeypatch):
    supplied = state()
    before = pickle.dumps(supplied)
    with monkeypatch.context() as guarded, patch.object(EconomicCalendarEngine, "evaluate", side_effect=AssertionError):
        spies = guard_side_effects(guarded)
        first = render_calendar(supplied)
        second = render_calendar(supplied)
        assert all(spy.call_count == 0 for spy in spies)
    assert first == second
    assert pickle.dumps(supplied) == before
    assert "\\n" in first
    assert payload(first)["next_event"]["title"] == supplied.next_event.title


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_calendar_presentation_preserves_official_context(direction):
    context = prepared(direction)
    context.economic_calendar = state()
    before = pickle.dumps(context)
    render_calendar(context.economic_calendar)
    assert pickle.dumps(context) == before
    assert context.decision.action == direction


@pytest.mark.parametrize("invalid", [False, 1, {}, "calendar"])
def test_wrong_input_is_rejected(invalid):
    with pytest.raises(TypeError):
        render_calendar(invalid)


def test_nonobservational_or_naive_evidence_is_rejected():
    with pytest.raises(ValueError):
        render_calendar(replace(state(), observational_only=False))
    with pytest.raises(ValueError):
        render_calendar(replace(state(), observed_at=NOW.replace(tzinfo=None)))
    with pytest.raises(ValueError):
        render_calendar(replace(state(), minutes_to_next=float("nan")))



@pytest.mark.parametrize("enabled", [False, True, 1, "true", None])
def test_bot_calendar_activation_is_explicit_and_context_is_preserved(enabled):
    from contextlib import redirect_stdout
    import io
    from app.bot import Bot

    context = prepared()
    context.economic_calendar = state()
    before = pickle.dumps(context)
    output = io.StringIO()
    with patch("app.bot.render_calendar", wraps=render_calendar) as renderer:
        with redirect_stdout(output):
            object.__new__(Bot).mostrar(
                context, calendar_presentation_enabled=enabled
            )
    assert renderer.call_count == int(enabled is True)
    assert pickle.dumps(context) == before
    assert "OFFICIAL DECISION: BUY" in output.getvalue()
    if enabled is True:
        assert context.economic_calendar.next_event.title.replace("\n", "\\n") in output.getvalue()
    elif enabled is False:
        assert "ECONOMIC CALENDAR" not in output.getvalue()
    else:
        assert "ECONOMIC CALENDAR OBSERVATIONAL UNAVAILABLE" in output.getvalue()


def test_bot_calendar_failure_preserves_external_presentation():
    from contextlib import redirect_stdout
    import io
    from app.bot import Bot

    context = prepared()
    before = pickle.dumps(context)
    output = io.StringIO()
    with patch("app.bot.render_calendar", side_effect=ValueError("synthetic failure")):
        with redirect_stdout(output):
            object.__new__(Bot).mostrar(
                context,
                calendar_presentation_enabled=True,
                external_presentation_enabled=True,
            )
    assert pickle.dumps(context) == before
    assert "OFFICIAL DECISION: BUY" in output.getvalue()
    assert "ECONOMIC CALENDAR OBSERVATIONAL UNAVAILABLE" in output.getvalue()
    assert "EXTERNAL OBSERVATIONAL DATA UNAVAILABLE" in output.getvalue()

