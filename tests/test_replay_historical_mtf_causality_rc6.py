"""RC6 - causalidade e determinismo do MTF histórico."""

from dataclasses import fields
from datetime import datetime, timedelta

from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from core.analysis_context import AnalysisContext
from models.candle import Candle
from replay.historical_multi_timeframe import (
    HistoricalMultiTimeframeBuilder,
)


T0 = datetime(2026, 10, 7, 10, 0)


def bar(minute):
    base = 100.0 + minute * 0.50

    return Candle(
        open=base,
        high=base + 1.0,
        low=base - 1.0,
        close=base + 0.25,
        volume=100.0 + minute,
        timestamp=T0 + timedelta(minutes=minute),
    )


def result_snapshot(result):
    return {
        field.name: getattr(result, field.name)
        for field in fields(result)
    }


def build_until(last_minute):
    builder = HistoricalMultiTimeframeBuilder(
        "WINV26"
    )

    for minute in range(last_minute + 1):
        builder.update(
            bar(minute)
        )

    return builder


def analyze(builder):
    context = AnalysisContext()

    context.multi_timeframe = builder

    result_context = (
        MultiTimeframeAnalysis().executar(
            context
        )
    )

    assert result_context is context

    return result_snapshot(
        context.multi_timeframe_analysis
    )


def market_snapshot(builder):
    snapshot = {}

    for timeframe in ("M1", "M5", "M15"):
        market = builder.get(timeframe)

        snapshot[timeframe] = [
            (
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
                candle.timestamp,
            )
            for candle in market.candles.all()
        ]

    return snapshot


def test_two_independent_reconstructions_are_identical():
    first = build_until(90)
    second = build_until(90)

    assert market_snapshot(first) == (
        market_snapshot(second)
    )

    assert analyze(first) == analyze(second)


def test_analysis_is_deterministic_on_same_history():
    builder = build_until(90)

    first = analyze(builder)
    second = analyze(builder)

    assert first == second


def test_future_data_does_not_change_prior_snapshot():
    builder = build_until(90)

    prior_market = market_snapshot(builder)
    prior_analysis = analyze(builder)

    for minute in range(91, 121):
        builder.update(
            bar(minute)
        )

    future_market = market_snapshot(builder)
    future_analysis = analyze(builder)

    # O futuro deve naturalmente alterar o estado atual.
    assert future_market != prior_market

    # Reconstruir somente até T=90 deve reproduzir
    # exatamente o estado e análise originalmente vistos em T=90.
    reconstructed_prior = build_until(90)

    assert market_snapshot(
        reconstructed_prior
    ) == prior_market

    assert analyze(
        reconstructed_prior
    ) == prior_analysis

    # Não exigimos que a análise futura seja diferente:
    # uma tendência pode legitimamente permanecer igual.
    assert future_analysis is not None


def test_prefix_reconstruction_is_causal_at_multiple_points():
    for cutoff in (
        15,
        30,
        45,
        60,
        75,
        90,
    ):
        first = build_until(cutoff)
        second = build_until(cutoff)

        assert market_snapshot(
            first
        ) == market_snapshot(
            second
        )

        assert analyze(first) == analyze(second)


def test_no_future_candle_exists_in_prefix():
    cutoff = 60

    builder = build_until(cutoff)

    cutoff_timestamp = (
        T0 + timedelta(minutes=cutoff)
    )

    for timeframe in ("M1", "M5", "M15"):
        for candle in (
            builder.get(
                timeframe
            ).candles.all()
        ):
            assert (
                candle.timestamp
                <= cutoff_timestamp
            )


def test_closed_counts_match_historical_state():
    builder = build_until(90)

    result = analyze(builder)

    assert result[
        "closed_candle_counts"
    ]["M1"] == (
        builder.get("M1").candle_count - 1
    )

    assert result[
        "closed_candle_counts"
    ]["M5"] == (
        builder.get("M5").candle_count - 1
    )

    assert result[
        "closed_candle_counts"
    ]["M15"] == (
        builder.get("M15").candle_count - 1
    )


def test_analysis_does_not_mutate_historical_market():
    builder = build_until(90)

    before = market_snapshot(builder)

    analyze(builder)

    after = market_snapshot(builder)

    assert after == before


def test_builder_can_supply_analysis_context_directly():
    builder = build_until(90)

    context = AnalysisContext(
        market=builder.primary,
        multi_timeframe=builder,
    )

    returned = (
        MultiTimeframeAnalysis().executar(
            context
        )
    )

    assert returned is context

    assert (
        context.multi_timeframe_analysis
        .closed_candle_counts["M1"]
        == builder.get("M1").candle_count - 1
    )

    assert (
        context.multi_timeframe_analysis
        .closed_candle_counts["M5"]
        == builder.get("M5").candle_count - 1
    )

    assert (
        context.multi_timeframe_analysis
        .closed_candle_counts["M15"]
        == builder.get("M15").candle_count - 1
    )