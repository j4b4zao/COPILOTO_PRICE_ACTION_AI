"""RC7.1 synthetic contract fixtures; no strategy performance evidence."""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import ast
from pathlib import Path

import pytest

from models.book_depth import BookLevel
from replay.historical_input_contract import AVAILABLE, UNAVAILABLE
from replay.historical_order_flow import (
    HistoricalTradeEvent, HistoricalBookSnapshot, HistoricalOrderFlowSnapshot,
    HistoricalOrderFlowBuilder, HistoricalOrderFlowValidationError,
)

T0 = datetime(2026, 10, 8, 10, tzinfo=timezone.utc)
T1 = T0 + timedelta(minutes=1)


def trade(**kwargs):
    return HistoricalTradeEvent(**dict(timestamp=T0 + timedelta(seconds=10),
        observed_at=T0 + timedelta(seconds=11), price=100., quantity=2.,
        aggressor="BUY", source_id="SYNTHETIC_FIXTURE_SESSION_A", event_id="1") | kwargs)


def book(**kwargs):
    return HistoricalBookSnapshot(**dict(observed_at=T1, source_id="SYNTHETIC_BOOK",
        bids=(BookLevel(99, 10),), asks=(BookLevel(101, 20),),
        integrity_verified=True, complete=True) | kwargs)


def build(events=(), **kwargs):
    return HistoricalOrderFlowBuilder.build(T1, events, **dict(period_start=T0,
        observation_complete=True) | kwargs)


@pytest.mark.parametrize("obj", [trade(), book(), build([trade()])])
def test_contracts_are_frozen(obj):
    with pytest.raises(FrozenInstanceError):
        setattr(obj, next(iter(obj.__dataclass_fields__)), None)


def test_deep_immutability_and_input_not_mutated():
    events = [trade()]
    levels = [BookLevel(99, 10)]
    b = book(bids=levels)
    s = build(events, book=b)
    events.clear()
    levels.clear()
    assert s.trades == (trade(),)
    assert b.bids == (BookLevel(99, 10),)
    with pytest.raises(FrozenInstanceError):
        s.book.bids[0].quantity = 999


def test_deterministic_order_and_metrics():
    buy = trade()
    sell = trade(event_id="2", quantity=3, aggressor="SELL")
    unknown = trade(event_id="3", quantity=5, aggressor="UNKNOWN")
    a = build([buy, sell, unknown])
    assert a == build([unknown, sell, buy])
    assert (a.status, a.buy_quantity, a.sell_quantity, a.unknown_quantity,
            a.total_quantity, a.delta) == (AVAILABLE, 2, 3, 5, 10, -1)


@pytest.mark.parametrize("field", ["timestamp", "observed_at"])
def test_future_events_rejected(field):
    kwargs = {field: T1 + timedelta(seconds=1)}
    if field == "timestamp":
        kwargs["observed_at"] = T1 + timedelta(seconds=2)
    with pytest.raises(HistoricalOrderFlowValidationError, match="FUTURE_EVENT"):
        build([trade(**kwargs)])


def test_observation_before_event_rejected():
    with pytest.raises(HistoricalOrderFlowValidationError, match="OBSERVATION_BEFORE_EVENT"):
        trade(observed_at=T0)


@pytest.mark.parametrize("field", ["timestamp", "observed_at"])
@pytest.mark.parametrize("value", [None, "2026-10-08", 42])
def test_invalid_event_timestamps(field, value):
    with pytest.raises(HistoricalOrderFlowValidationError, match="TIMESTAMP_REQUIRED"):
        trade(**{field: value})


@pytest.mark.parametrize("field", ["price", "quantity"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "2"])
def test_invalid_numbers(field, value):
    with pytest.raises(HistoricalOrderFlowValidationError, match="INVALID_NUMBER"):
        trade(**{field: value})


def test_mixed_timezone_fails_with_audit_code():
    with pytest.raises(HistoricalOrderFlowValidationError) as exc:
        trade(timestamp=T0.replace(tzinfo=None))
    assert exc.value.reason == "INCOMPATIBLE_TIMESTAMPS"


def test_event_at_cutoff_is_allowed():
    assert build([trade(timestamp=T1, observed_at=T1)]).available


@pytest.mark.parametrize("stamp", [T0, T0 - timedelta(seconds=1)])
def test_event_outside_explicit_period(stamp):
    with pytest.raises(HistoricalOrderFlowValidationError, match="EVENT_OUTSIDE_PERIOD"):
        build([trade(timestamp=stamp)])


def test_duplicate_identity_not_double_counted():
    event = trade()
    assert build([event, event, replace(event, observed_at=T1)]) == build([event])
    assert build([event, event]).total_quantity == 2


def test_conflicting_duplicate_identity_rejected():
    with pytest.raises(HistoricalOrderFlowValidationError, match="CONFLICTING_EVENT_ID"):
        build([trade(), trade(quantity=3)])


def test_identical_economic_trades_with_distinct_ids_preserved():
    assert build([trade(), trade(event_id="2")]).total_quantity == 4


def test_identity_scoped_to_source():
    assert build([trade(), trade(source_id="SYNTHETIC_SESSION_B")]).total_quantity == 4


def test_missing_identity_fails_closed_instead_of_inventing_dedup():
    s = build([trade(event_id=None), trade(event_id=None)])
    assert s.reason == "EVENT_IDENTITY_UNVERIFIABLE"
    assert s.total_quantity is None and s.valid_trades == ()


def test_unknown_aggressor_remains_unknown():
    s = build([trade(aggressor="unknown")])
    assert s.trades[0].aggressor == "UNKNOWN"
    assert s.delta is None and s.unknown_quantity == 2


def test_unrecognized_side_not_inferred():
    with pytest.raises(HistoricalOrderFlowValidationError, match="INVALID_AGGRESSOR"):
        trade(aggressor="RLP")


def test_balanced_classified_delta_is_real_zero():
    assert build([trade(), trade(event_id="2", aggressor="SELL")]).delta == 0


@pytest.mark.parametrize("source", ["", " ", "UNKNOWN", "UNAVAILABLE"])
def test_missing_provenance_unavailable(source):
    s = build([trade(source_id=source)])
    assert s.status == UNAVAILABLE and s.reason == "PROVENANCE_MISSING"
    assert s.delta is None and s.provenance == ()


def test_gap_discards_current_book_and_disables_metrics():
    builder = HistoricalOrderFlowBuilder()
    assert builder.build(T1, [trade()], book(), period_start=T0,
                         observation_complete=True).available
    gap = builder.build(T1, [trade()], book(), period_start=T0)
    assert gap.reason == "OBSERVATION_GAP" and gap.book is None
    assert gap.delta is None and gap.valid_trades == ()
    assert builder.build(T1, period_start=T0, observation_complete=True).book is None


def test_empty_input_is_unavailable_not_zero():
    s = build()
    assert s.reason == "NO_TRADE_EVENTS" and s.delta is None and s.total_quantity is None


def test_period_unknown_is_unavailable():
    assert build([trade()], period_start=None).reason == "PERIOD_UNKNOWN"


@pytest.mark.parametrize("start", [T1, T1 + timedelta(seconds=1)])
def test_invalid_period(start):
    with pytest.raises(HistoricalOrderFlowValidationError, match="INVALID_PERIOD"):
        build([trade()], period_start=start)


def test_book_optional_without_disabling_trade_evidence():
    assert build([trade()]).available and build([trade()]).book is None


@pytest.mark.parametrize("kwargs", [dict(source_id=""), dict(complete=False),
    dict(integrity_verified=False), dict(bids=()), dict(asks=()),
    dict(observed_at=T0)])
def test_unavailable_or_stale_book_not_promoted(kwargs):
    assert build([trade()], book=book(**kwargs)).book is None


def test_current_explicit_complete_book_retained():
    assert build([trade()], book=book()).book == book()


def test_future_book_rejected_even_without_provenance():
    with pytest.raises(HistoricalOrderFlowValidationError, match="FUTURE_BOOK"):
        build([trade()], book=book(observed_at=T1 + timedelta(seconds=1), source_id=""))


@pytest.mark.parametrize("level", [BookLevel(float("nan"), 1), BookLevel(99, float("inf")),
    BookLevel(99, 1, True)])
def test_book_levels_receive_stricter_historical_validation(level):
    with pytest.raises(HistoricalOrderFlowValidationError):
        book(bids=[level])


def test_crossed_book_rejected():
    with pytest.raises(HistoricalOrderFlowValidationError, match="CROSSED_BOOK"):
        book(bids=[BookLevel(102, 1)])


def test_unsorted_book_rejected():
    with pytest.raises(HistoricalOrderFlowValidationError, match="UNSORTED_BIDS"):
        book(bids=[BookLevel(98, 1), BookLevel(99, 1)])


def test_repetition_and_session_isolation():
    a, b = HistoricalOrderFlowBuilder(), HistoricalOrderFlowBuilder()
    first = build([trade()])
    for _ in range(3):
        assert a.build(T1, [trade()], period_start=T0, observation_complete=True) == first
    assert b.build(T1, period_start=T0, observation_complete=True).trades == ()
    assert a.build(T1, period_start=T0, observation_complete=True).trades == ()


def test_historical_prefix_not_changed_by_later_build():
    prefix = build([trade()])
    later = HistoricalOrderFlowBuilder.build(T1 + timedelta(minutes=1),
        [trade(), trade(timestamp=T1, observed_at=T1, event_id="2")],
        period_start=T0, observation_complete=True)
    assert later.total_quantity == 4
    assert prefix == build([trade()]) and prefix.total_quantity == 2


def test_direct_snapshot_cannot_bypass_validation_or_dedup():
    assert HistoricalOrderFlowSnapshot(T1, T0, [trade(), trade()], None, True) == build([trade()])
    with pytest.raises(HistoricalOrderFlowValidationError, match="FUTURE_EVENT"):
        HistoricalOrderFlowSnapshot(T0, trades=[trade()])


def test_overflowing_aggregate_rejected():
    with pytest.raises(HistoricalOrderFlowValidationError, match="INVALID_NUMBER"):
        build([trade(quantity=1e308), trade(quantity=1e308, event_id="2")])


def test_module_has_no_operational_or_live_dependencies():
    path = Path(__file__).resolve().parents[1] / "replay/historical_order_flow.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    imports = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert imports == {"__future__", "dataclasses", "datetime", "models.book_depth",
                       "replay.historical_input_contract"}
    assert {n.name for n in ast.walk(tree) if isinstance(n, ast.Import) for n in n.names} == {"math"}
    assert not any(isinstance(n, ast.Attribute) and n.attr in {"now", "utcnow", "today"}
                   for n in ast.walk(tree))


@pytest.mark.parametrize("value", [None, 1, True])
def test_invalid_collection_has_audit_reason(value):
    with pytest.raises(HistoricalOrderFlowValidationError, match="INVALID_COLLECTION"):
        build(value)


@pytest.mark.parametrize("field", ["observation_complete"])
def test_boolean_flags_are_explicit(field):
    with pytest.raises(HistoricalOrderFlowValidationError, match="INVALID_COMPLETENESS"):
        build([trade()], **{field: 1})


def test_new_period_does_not_accept_old_events_after_gap():
    with pytest.raises(HistoricalOrderFlowValidationError, match="EVENT_OUTSIDE_PERIOD"):
        HistoricalOrderFlowBuilder.build(T1 + timedelta(minutes=1), [trade()],
            period_start=T1, observation_complete=True)


def test_unavailable_provenance_still_cannot_hide_future():
    with pytest.raises(HistoricalOrderFlowValidationError, match="FUTURE_EVENT"):
        build([trade(timestamp=T1, observed_at=T1 + timedelta(seconds=1), source_id="")])


@pytest.mark.parametrize("source", ["synthetic_fixture_session_a", "Synthetic_Fixture_Session_A",
    " SYNTHETIC_FIXTURE_SESSION_A "])
def test_source_aliases_canonicalize_and_deduplicate(source):
    original = trade()
    alias = trade(source_id=source)
    assert alias.source_id == original.source_id
    assert alias.timestamp == original.timestamp and alias.observed_at == original.observed_at
    s = build([original, alias])
    assert s.available and s.valid_trades == (original,)
    assert s.total_quantity == s.delta == 2
    assert s == build([alias, original, original])


@pytest.mark.parametrize("changes", [dict(price=101), dict(quantity=3), dict(aggressor="SELL"),
    dict(timestamp=T0+timedelta(seconds=9))])
def test_canonical_identity_rejects_conflicting_economic_event(changes):
    alias = trade(source_id="synthetic_fixture_session_a", **changes)
    with pytest.raises(HistoricalOrderFlowValidationError, match="CONFLICTING_EVENT_ID"):
        build([trade(), alias])
    with pytest.raises(HistoricalOrderFlowValidationError, match="CONFLICTING_EVENT_ID"):
        build([alias, trade()])


def test_distinct_event_ids_survive_case_aliases():
    s = build([trade(), trade(source_id="synthetic_fixture_session_a", event_id="2")])
    assert len(s.trades) == 2 and s.total_quantity == s.delta == 4


def test_event_ids_remain_case_sensitive_and_are_not_fabricated():
    s = build([trade(event_id="Trade"), trade(event_id="trade")])
    assert len(s.trades) == 2 and s.total_quantity == 4
    assert trade(event_id=None).event_id is None
    assert not build([trade(event_id=None)]).available


def test_real_different_sources_remain_distinct_after_normalization():
    s = build([trade(), trade(source_id=" different_source ")])
    assert len(s.trades) == 2 and s.total_quantity == s.delta == 4
    assert "DIFFERENT_SOURCE" in s.provenance


def test_source_normalization_matches_rc5_and_book_contract():
    from replay.historical_input_contract import HistoricalDomainObservation
    source = " synthetic_source "
    expected = HistoricalDomainObservation("ORDER_FLOW", "AVAILABLE", T1, source).source
    assert trade(source_id=source).source_id == book(source_id=source).source_id == expected


def test_canonical_prefix_and_repeated_sequence_are_deterministic():
    first = trade()
    alias = trade(source_id="synthetic_fixture_session_a")
    prefix = build([first, alias])
    extended = build([alias, first, trade(event_id="2", aggressor="SELL")])
    assert prefix == build([alias, first])
    assert prefix.total_quantity == prefix.delta == 2
    assert extended.total_quantity == 4 and extended.delta == 0
    assert extended == build(list(reversed(extended.trades)))
