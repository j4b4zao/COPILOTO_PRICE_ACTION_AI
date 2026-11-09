"""Acceptance coverage for local headline evidence."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import pickle

import pytest

from economic_context.local_news import LocalNewsState, evaluate_local_news
from tests.test_copilot_readonly_dashboard_rc1 import prepared, guard_side_effects


NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
AGE = timedelta(minutes=10)


def row(id="1", stamp="2026-11-09T11:55:00+00:00", **values):
    return dict(id=id, title="Synthetic headline", source="LOCAL", published_at=stamp, **values)


def evaluate(payload):
    return evaluate_local_news(payload, now=NOW, max_age=AGE)


def test_timezone_equivalence_and_original_text_are_preserved():
    first = row("1", "2026-11-09T11:55:00+00:00")
    second = row("2", "2026-11-09T08:55:00-03:00")
    result = evaluate([second, first])
    assert result.status == "READY"
    a, b = result.headlines
    assert a.published_at_utc == b.published_at_utc
    assert a.published_at == first["published_at"]
    assert b.published_at == second["published_at"]
    assert a.freshness == b.freshness == "FRESH"
    assert result.observational_only is True


@pytest.mark.parametrize("stamp,expected", [
    ("2026-11-09T11:49:59.999999+00:00", "STALE"),
    ("2026-11-09T11:50:00+00:00", "FRESH"),
    ("2026-11-09T12:00:00+00:00", "FRESH"),
    ("2026-11-09T12:00:00.000001+00:00", "FUTURE"),
])
def test_age_boundaries(stamp, expected):
    assert evaluate([row(stamp=stamp)]).headlines[0].freshness == expected


def test_duplicates_order_and_source_identity():
    a = row("2")
    b = row("1")
    c = dict(b, source="OTHER")
    assert evaluate([a, b, a, c]) == evaluate([c, b, a])
    assert len(evaluate([a, b, a, c]).headlines) == 3
    conflict = dict(b, title="Conflicting headline")
    result = evaluate([a, b, conflict])
    assert result.status == "UNAVAILABLE"
    assert result.headlines == ()
    assert result.reasons == ("CONFLICTING_DUPLICATE",)


@pytest.mark.parametrize("payload", [
    None, {}, "news", [{}], [row(), {}],
    [dict(row(), id=" ")], [dict(row(), title=1)],
    [dict(row(), published_at="2026-11-09T11:55:00")],
    [dict(row(), published_at="invalid")], [dict(row(), extra=True)],
])
def test_invalid_batches_fail_without_partial_results(payload):
    result = evaluate(payload)
    assert result.status == "UNAVAILABLE"
    assert result.headlines == ()


def test_empty_input_and_explicit_parameters():
    assert evaluate([]).status == "NO_NEWS"
    with pytest.raises(ValueError):
        evaluate_local_news([], now=NOW.replace(tzinfo=None), max_age=AGE)
    for age in (timedelta(0), timedelta(seconds=-1), 10, True):
        with pytest.raises(ValueError):
            evaluate_local_news([], now=NOW, max_age=age)


def test_immutability_and_no_operational_side_effects(monkeypatch):
    context = prepared()
    payload = [dict(row(), title='<tag>"\\nReported')]
    before = pickle.dumps((context, payload))
    with monkeypatch.context() as guarded:
        spies = guard_side_effects(guarded)
        result = evaluate(payload)
        assert all(spy.call_count == 0 for spy in spies)
    assert pickle.dumps((context, payload)) == before
    assert result.headlines[0].title == payload[0]["title"]
    with pytest.raises(FrozenInstanceError):
        result.headlines[0].title = "changed"
    items = list(result.headlines)
    copy = LocalNewsState("READY", NOW.isoformat(), items)
    items.clear()
    assert copy.headlines == result.headlines

