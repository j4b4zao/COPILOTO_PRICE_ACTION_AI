"""Replay RC5 historical causal input contract."""

from datetime import datetime, timedelta, timezone

import pytest

from replay.historical_input_contract import (
    AVAILABLE,
    UNAVAILABLE,
    HISTORICAL_DOMAINS,
    HistoricalDomainObservation,
    ReplayHistoricalInput,
)


BASE = datetime(
    2026,
    9,
    23,
    10,
    30,
)


def unavailable(domain):
    return HistoricalDomainObservation(
        domain=domain,
        status=UNAVAILABLE,
        reason="NOT_CAPTURED",
    )


def available(
    domain,
    *,
    observed_at=BASE,
    source="CONTROLLED_HISTORY",
):
    return HistoricalDomainObservation(
        domain=domain,
        status=AVAILABLE,
        observed_at=observed_at,
        source=source,
    )


def historical_input(
    *,
    candle_timestamp=BASE,
    mtf=None,
    order_flow=None,
    external=None,
    economic_calendar=None,
    book_depth=None,
):
    return ReplayHistoricalInput(
        candle_timestamp=candle_timestamp,
        mtf=mtf or unavailable("MTF"),
        order_flow=order_flow or unavailable(
            "ORDER_FLOW"
        ),
        external=external or unavailable(
            "EXTERNAL"
        ),
        economic_calendar=(
            economic_calendar
            or unavailable("ECONOMIC_CALENDAR")
        ),
        book_depth=book_depth or unavailable(
            "BOOK_DEPTH"
        ),
    )


def test_all_domains_are_explicit():
    assert HISTORICAL_DOMAINS == (
        "MTF",
        "ORDER_FLOW",
        "EXTERNAL",
        "ECONOMIC_CALENDAR",
        "BOOK_DEPTH",
    )


def test_unavailable_factory_is_fail_closed():
    result = ReplayHistoricalInput.unavailable(
        BASE
    )

    assert result.available_domains == ()
    assert result.unavailable_domains == (
        "MTF",
        "ORDER_FLOW",
        "EXTERNAL",
        "ECONOMIC_CALENDAR",
        "BOOK_DEPTH",
    )

    for observation in result.observations:
        assert observation.status == UNAVAILABLE
        assert observation.observed_at is None


def test_available_requires_timestamp():
    with pytest.raises(
        ValueError,
        match="observed_at",
    ):
        HistoricalDomainObservation(
            domain="MTF",
            status=AVAILABLE,
            source="CONTROLLED_HISTORY",
        )


def test_available_requires_source():
    with pytest.raises(
        ValueError,
        match="source",
    ):
        HistoricalDomainObservation(
            domain="MTF",
            status=AVAILABLE,
            observed_at=BASE,
        )


def test_unavailable_cannot_carry_observed_at():
    with pytest.raises(
        ValueError,
        match="UNAVAILABLE",
    ):
        HistoricalDomainObservation(
            domain="MTF",
            status=UNAVAILABLE,
            observed_at=BASE,
        )


def test_unknown_domain_is_rejected():
    with pytest.raises(
        ValueError,
        match="Domínio histórico inválido",
    ):
        HistoricalDomainObservation(
            domain="UNKNOWN",
            status=UNAVAILABLE,
        )


def test_unknown_status_is_rejected():
    with pytest.raises(
        ValueError,
        match="Status histórico inválido",
    ):
        HistoricalDomainObservation(
            domain="MTF",
            status="STALE",
        )


def test_same_timestamp_is_causal():
    result = historical_input(
        mtf=available(
            "MTF",
            observed_at=BASE,
        ),
    )

    assert result.available_domains == (
        "MTF",
    )

    assert result.status_for("MTF") == AVAILABLE


def test_older_timestamp_is_causal():
    result = historical_input(
        order_flow=available(
            "ORDER_FLOW",
            observed_at=BASE - timedelta(seconds=1),
        ),
    )

    assert result.available_domains == (
        "ORDER_FLOW",
    )


def test_future_observation_is_rejected():
    with pytest.raises(
        ValueError,
        match="observação futura",
    ):
        historical_input(
            mtf=available(
                "MTF",
                observed_at=BASE + timedelta(seconds=1),
            ),
        )


def test_mixed_available_and_unavailable_domains():
    result = historical_input(
        mtf=available("MTF"),
        order_flow=available("ORDER_FLOW"),
    )

    assert result.available_domains == (
        "MTF",
        "ORDER_FLOW",
    )

    assert result.unavailable_domains == (
        "EXTERNAL",
        "ECONOMIC_CALENDAR",
        "BOOK_DEPTH",
    )


def test_wrong_domain_in_slot_is_rejected():
    with pytest.raises(
        ValueError,
        match="Domínios históricos",
    ):
        historical_input(
            mtf=available(
                "ORDER_FLOW"
            ),
        )


def test_status_lookup_normalizes_name():
    result = historical_input(
        mtf=available("MTF"),
    )

    assert result.status_for("mtf") == AVAILABLE
    assert (
        result.status_for(" order_flow ")
        == UNAVAILABLE
    )


def test_unknown_status_lookup_is_rejected():
    result = historical_input()

    with pytest.raises(
        ValueError,
        match="Domínio histórico inválido",
    ):
        result.status_for("UNKNOWN")


def test_contract_is_immutable():
    result = historical_input()

    with pytest.raises(
        AttributeError,
    ):
        result.candle_timestamp = (
            BASE + timedelta(minutes=1)
        )


def test_timezone_aware_timestamps_are_supported():
    timestamp = datetime(
        2026,
        9,
        23,
        13,
        30,
        tzinfo=timezone.utc,
    )

    result = ReplayHistoricalInput.unavailable(
        timestamp
    )

    assert result.candle_timestamp == timestamp


def test_incompatible_timezone_semantics_fail_closed():
    aware = datetime(
        2026,
        9,
        23,
        13,
        30,
        tzinfo=timezone.utc,
    )

    observation = available(
        "MTF",
        observed_at=aware,
    )

    with pytest.raises(
        ValueError,
        match="semântica temporal incompatível",
    ):
        historical_input(
            candle_timestamp=BASE,
            mtf=observation,
        )