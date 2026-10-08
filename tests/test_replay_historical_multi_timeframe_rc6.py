"""Replay RC6 historical multi-timeframe reconstruction."""

from datetime import datetime, timedelta

import pytest

from models.candle import Candle
from replay.historical_multi_timeframe import (
    HistoricalMultiTimeframeBuilder,
)


T0 = datetime(
    2026,
    10,
    7,
    10,
    0,
)


def bar(
    minute,
    *,
    open=100,
    high=101,
    low=99,
    close=100,
    volume=10,
):
    return Candle(
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=T0 + timedelta(
            minutes=minute
        ),
    )


def test_first_m1_creates_all_timeframes():
    builder = (
        HistoricalMultiTimeframeBuilder(
            "WINV26"
        )
    )

    created = builder.update(
        bar(0)
    )

    assert created == {
        "M1": True,
        "M5": True,
        "M15": True,
    }

    assert builder.get(
        "M1"
    ).candle_count == 1

    assert builder.get(
        "M5"
    ).candle_count == 1

    assert builder.get(
        "M15"
    ).candle_count == 1


def test_m1_preserves_real_ohlcv():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    source = bar(
        0,
        open=100,
        high=110,
        low=95,
        close=105,
        volume=321,
    )

    builder.update(source)

    result = builder.get(
        "M1"
    ).last_candle

    assert result is not source

    assert (
        result.open,
        result.high,
        result.low,
        result.close,
        result.volume,
    ) == (
        100,
        110,
        95,
        105,
        321,
    )


def test_m5_aggregates_real_m1_ohlcv():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    builder.update(
        bar(
            0,
            open=100,
            high=103,
            low=99,
            close=102,
            volume=10,
        )
    )

    builder.update(
        bar(
            1,
            open=102,
            high=108,
            low=101,
            close=107,
            volume=20,
        )
    )

    builder.update(
        bar(
            2,
            open=107,
            high=109,
            low=96,
            close=98,
            volume=30,
        )
    )

    result = builder.get(
        "M5"
    ).last_candle

    assert result.open == 100
    assert result.high == 109
    assert result.low == 96
    assert result.close == 98
    assert result.volume == 60

    assert result.timestamp == T0


def test_m15_aggregates_real_m1_ohlcv():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    for minute in range(15):
        builder.update(
            bar(
                minute,
                open=100 + minute,
                high=105 + minute,
                low=95 - minute,
                close=101 + minute,
                volume=minute + 1,
            )
        )

    result = builder.get(
        "M15"
    ).last_candle

    assert result.open == 100
    assert result.high == 119
    assert result.low == 81
    assert result.close == 115

    assert result.volume == sum(
        range(1, 16)
    )

    assert result.timestamp == T0


def test_new_m5_period_closes_previous_window():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    for minute in range(6):
        builder.update(
            bar(
                minute,
                open=100 + minute,
                high=101 + minute,
                low=99 + minute,
                close=100 + minute,
            )
        )

    m5 = builder.get("M5")
    candles = m5.candles.all()

    assert len(candles) == 2

    closed = candles[0]
    current = candles[1]

    assert closed.timestamp == T0

    assert current.timestamp == (
        T0 + timedelta(minutes=5)
    )

    assert current.close == 105


def test_new_m15_period_closes_previous_window():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    for minute in range(16):
        builder.update(
            bar(
                minute,
                open=100 + minute,
                high=101 + minute,
                low=99 + minute,
                close=100 + minute,
            )
        )

    candles = builder.get(
        "M15"
    ).candles.all()

    assert len(candles) == 2

    assert candles[0].timestamp == T0

    assert candles[1].timestamp == (
        T0 + timedelta(minutes=15)
    )


def test_period_boundaries_are_reported():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    assert builder.update(
        bar(0)
    ) == {
        "M1": True,
        "M5": True,
        "M15": True,
    }

    assert builder.update(
        bar(1)
    ) == {
        "M1": True,
        "M5": False,
        "M15": False,
    }

    assert builder.update(
        bar(5)
    ) == {
        "M1": True,
        "M5": True,
        "M15": False,
    }

    assert builder.update(
        bar(15)
    ) == {
        "M1": True,
        "M5": True,
        "M15": True,
    }


def test_missing_minutes_are_not_fabricated():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    builder.update(
        bar(
            0,
            open=100,
            high=102,
            low=99,
            close=101,
            volume=10,
        )
    )

    builder.update(
        bar(
            4,
            open=101,
            high=110,
            low=100,
            close=109,
            volume=20,
        )
    )

    m1 = builder.get("M1")
    m5 = builder.get("M5")

    assert m1.candle_count == 2
    assert m5.candle_count == 1

    aggregate = m5.last_candle

    assert aggregate.open == 100
    assert aggregate.high == 110
    assert aggregate.low == 99
    assert aggregate.close == 109
    assert aggregate.volume == 30


def test_gap_across_period_creates_only_observed_period():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    builder.update(
        bar(0)
    )

    builder.update(
        bar(10)
    )

    m5 = builder.get("M5")

    assert m5.candle_count == 2

    timestamps = [
        candle.timestamp
        for candle in m5.candles.all()
    ]

    assert timestamps == [
        T0,
        T0 + timedelta(minutes=10),
    ]


def test_duplicate_timestamp_is_rejected_without_mutation():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    builder.update(
        bar(0)
    )

    before = builder.snapshot()

    with pytest.raises(
        ValueError,
        match="estritamente crescentes",
    ):
        builder.update(
            bar(0)
        )

    assert builder.snapshot() == before


def test_regressive_timestamp_is_rejected_without_mutation():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    builder.update(
        bar(1)
    )

    before = builder.snapshot()

    with pytest.raises(
        ValueError,
        match="estritamente crescentes",
    ):
        builder.update(
            bar(0)
        )

    assert builder.snapshot() == before


@pytest.mark.parametrize(
    "values",
    [
        {
            "open": 0,
        },
        {
            "high": float("nan"),
        },
        {
            "volume": -1,
        },
        {
            "open": 100,
            "high": 99,
            "low": 98,
            "close": 100,
        },
        {
            "open": 100,
            "high": 101,
            "low": 102,
            "close": 100,
        },
    ],
)
def test_invalid_ohlcv_is_rejected(
    values,
):
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    with pytest.raises(ValueError):
        builder.update(
            bar(
                0,
                **values,
            )
        )

    assert builder.get(
        "M1"
    ).candle_count == 0

    assert builder.get(
        "M5"
    ).candle_count == 0

    assert builder.get(
        "M15"
    ).candle_count == 0


def test_timestamp_is_required():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    source = bar(0)
    source.timestamp = None

    with pytest.raises(
        ValueError,
        match="timestamp",
    ):
        builder.update(source)


def test_input_candle_is_not_mutated():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    source = bar(
        0,
        open=100,
        high=110,
        low=90,
        close=105,
        volume=50,
    )

    before = source.to_dict().copy()

    builder.update(source)

    assert source.to_dict() == before


def test_historical_markets_are_independent():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    builder.update(
        bar(0)
    )

    assert (
        builder.get("M1")
        is not builder.get("M5")
    )

    assert (
        builder.get("M5")
        is not builder.get("M15")
    )

    assert (
        builder.get("M1").last_candle
        is not builder.get("M5").last_candle
    )


def test_snapshot_is_deterministic():
    first = (
        HistoricalMultiTimeframeBuilder(
            "WINV26"
        )
    )

    second = (
        HistoricalMultiTimeframeBuilder(
            "WINV26"
        )
    )

    candles = [
        bar(minute)
        for minute in range(20)
    ]

    for candle in candles:
        first.update(candle)

    for candle in candles:
        second.update(candle)

    assert first.snapshot() == second.snapshot()


def test_builder_exposes_mtf_analysis_compatible_interface():
    builder = (
        HistoricalMultiTimeframeBuilder()
    )

    for minute in range(76):
        builder.update(
            bar(
                minute,
                open=100 + minute,
                close=100 + minute,
                high=101 + minute,
                low=99 + minute,
            )
        )

    assert builder.primary is builder.get(
        "M1"
    )

    assert builder.get(
        "M1"
    ).candle_count == 76

    assert builder.get(
        "M5"
    ).candle_count == 16

    assert builder.get(
        "M15"
    ).candle_count == 6

    assert builder.all_ready is True