"""RC6.1 - explicit RC5 authorization for historical MTF replay integration."""

from datetime import datetime, timedelta

import pytest

from core.analysis_context import AnalysisContext
from models.candle import Candle
from replay.historical_input_contract import (
    AVAILABLE,
    UNAVAILABLE,
    HistoricalDomainObservation,
    ReplayHistoricalInput,
)
from replay.replay_engine import ReplayAbortedError, ReplayEngine


T0 = datetime(2026, 10, 7, 10)


def bar(minute):
    price = 100.0 + minute * 0.25
    return Candle(
        open=price,
        high=price + 1.0,
        low=price - 1.0,
        close=price + 0.10,
        volume=100.0 + minute,
        timestamp=T0 + timedelta(minutes=minute),
    )


def unavailable(domain):
    return HistoricalDomainObservation(
        domain=domain,
        status=UNAVAILABLE,
        reason="NOT_CAPTURED",
    )


def historical(timestamp, *, mtf=True):
    return ReplayHistoricalInput(
        candle_timestamp=timestamp,
        mtf=HistoricalDomainObservation(
            domain="MTF",
            status=AVAILABLE,
            observed_at=timestamp,
            source="CONTROLLED_M1_HISTORY",
        ) if mtf else unavailable("MTF"),
        order_flow=unavailable("ORDER_FLOW"),
        external=unavailable("EXTERNAL"),
        economic_calendar=unavailable("ECONOMIC_CALENDAR"),
        book_depth=unavailable("BOOK_DEPTH"),
    )


class ObservingPipeline:
    def __init__(self):
        self.seen = []

    def executar(self, context):
        state = context.multi_timeframe
        self.seen.append(
            None if state is None else {
                timeframe: tuple(
                    (
                        candle.open,
                        candle.high,
                        candle.low,
                        candle.close,
                        candle.volume,
                        candle.timestamp,
                    )
                    for candle in state.get(timeframe).candles.all()
                )
                for timeframe in ("M1", "M5", "M15")
            }
        )
        context.clear_results()
        return context


def engine():
    return ReplayEngine(ObservingPipeline(), trusted_offline=True)


def test_legacy_call_remains_mtf_unavailable():
    replay = engine()
    result = replay.executar(
        AnalysisContext(),
        [bar(0), bar(1)],
    )
    assert result.audit.completed
    # Session pipeline is deep-copied; original remains untouched.
    assert replay.pipeline.seen == []


def test_available_mtf_is_visible_to_pipeline_before_execution():
    class CheckingPipeline:
        def __init__(self):
            self.count = 0

        def executar(self, context):
            self.count += 1
            assert context.multi_timeframe is not None
            assert context.multi_timeframe.get("M1").candle_count == self.count
            assert context.multi_timeframe.get("M1").last_candle.timestamp == (
                T0 + timedelta(minutes=self.count - 1)
            )
            context.clear_results()
            return context

    candles = [bar(i) for i in range(3)]
    history = [historical(c.timestamp) for c in candles]

    result = ReplayEngine(
        CheckingPipeline(),
        trusted_offline=True,
    ).executar(
        AnalysisContext(),
        candles,
        historical_inputs=history,
    )

    assert result.audit.completed
    assert result.candles == 3


def test_mtf_unavailable_is_not_reused_from_prior_available_sample():
    class CheckingPipeline:
        def __init__(self):
            self.index = 0

        def executar(self, context):
            expected = (True, False, True)[self.index]
            assert (context.multi_timeframe is not None) is expected
            if expected:
                expected_count = 1 if self.index == 0 else 2
                assert context.multi_timeframe.get("M1").candle_count == expected_count
            self.index += 1
            context.clear_results()
            return context

    candles = [bar(i) for i in range(3)]
    history = [
        historical(candles[0].timestamp, mtf=True),
        historical(candles[1].timestamp, mtf=False),
        historical(candles[2].timestamp, mtf=True),
    ]

    result = ReplayEngine(
        CheckingPipeline(),
        trusted_offline=True,
    ).executar(
        AnalysisContext(),
        candles,
        historical_inputs=history,
    )

    assert result.audit.completed


def test_historical_timestamp_must_match_candle():
    candle = bar(0)
    wrong = historical(candle.timestamp + timedelta(minutes=1))

    with pytest.raises(ReplayAbortedError) as caught:
        engine().executar(
            AnalysisContext(),
            [candle],
            historical_inputs=[wrong],
        )

    assert caught.value.audit_snapshot.abort_stage == "HISTORICAL_INPUT"
    assert caught.value.audit_snapshot.candles_processed == 0


def test_missing_historical_item_fails_closed():
    candles = [bar(0), bar(1)]

    with pytest.raises(ReplayAbortedError) as caught:
        engine().executar(
            AnalysisContext(),
            candles,
            historical_inputs=[historical(candles[0].timestamp)],
        )

    assert caught.value.audit_snapshot.abort_stage == "HISTORICAL_INPUT"
    assert caught.value.audit_snapshot.candles_processed == 1


def test_extra_historical_item_fails_closed():
    candle = bar(0)
    history = [
        historical(candle.timestamp),
        historical(candle.timestamp + timedelta(minutes=1)),
    ]

    with pytest.raises(ReplayAbortedError) as caught:
        engine().executar(
            AnalysisContext(),
            [candle],
            historical_inputs=history,
        )

    assert caught.value.audit_snapshot.abort_stage == "HISTORICAL_INPUT"
    assert caught.value.audit_snapshot.candles_processed == 1


def test_wrong_historical_type_fails_closed():
    with pytest.raises(ReplayAbortedError) as caught:
        engine().executar(
            AnalysisContext(),
            [bar(0)],
            historical_inputs=[object()],
        )

    assert caught.value.audit_snapshot.abort_stage == "HISTORICAL_INPUT"
    assert caught.value.audit_snapshot.candles_processed == 0


def test_two_sessions_do_not_share_historical_mtf_state():
    class OneCandlePipeline:
        def executar(self, context):
            assert context.multi_timeframe is not None
            assert context.multi_timeframe.get("M1").candle_count == 1
            context.clear_results()
            return context

    replay = ReplayEngine(
        OneCandlePipeline(),
        trusted_offline=True,
    )

    for minute in (0, 10):
        candle = bar(minute)
        result = replay.executar(
            AnalysisContext(),
            [candle],
            historical_inputs=[historical(candle.timestamp)],
        )
        assert result.audit.completed
