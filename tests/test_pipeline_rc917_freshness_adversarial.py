"""Caracterização offline da frescura da cotação primária na RC9.17.

A fixture RC46 fornece confluências controladas. As cinco engines
operacionais executam seus próprios contratos sobre essas entradas.
"""

from datetime import datetime, timedelta, timezone

import pytest

from alerts import alert_manager
from analysis.analysis_pipeline import AnalysisPipeline
from analysis.temporal_snapshot_policy import PRIMARY_QUOTE_TEMPORAL_POLICY
from core.analysis_context import AnalysisContext
from tests.test_collector_multi_timeframe_rc31 import FakeExcel, FakeReader
from tests.test_order_flow_score_e2e_rc46 import prepare_confluences
from tests.test_trader_psychology_rc7 import build_pipeline
from market_data.collector import Collector


NOW = datetime(2026, 11, 18, 10, 0)
SYMBOL = "WINZ26"
OPERATIONAL_ENGINES = {
    "StrategyEngine", "ScoreEngine", "RiskManager", "DecisionEngine", "AlertManager",
}


class ControlledClock:
    def __init__(self):
        self.current = NOW

    def now(self):
        return self.current


class ControlledConfluences:
    ENABLED = True

    def executar(self, context):
        prepare_confluences(context, "BUY")
        return context


@pytest.fixture
def offline_chain(monkeypatch):
    clock = ControlledClock()
    monkeypatch.setattr(alert_manager, "datetime", clock)
    pipeline = AnalysisPipeline()
    engines = [engine for engine in pipeline.engines
               if type(engine).__name__ in OPERATIONAL_ENGINES]
    assert {type(engine).__name__ for engine in engines} == OPERATIONAL_ENGINES
    pipeline.engines = [ControlledConfluences(), *engines]
    return clock, pipeline


def quote(event_time, price=180_000.0, volume=1000.0):
    return {
        "ativo": SYMBOL,
        "data": event_time.date().isoformat(),
        "hora": event_time.timetz().isoformat(),
        "close": price,
        "volume": volume,
        "strike": None,
    }


def collector_for(clock, *quotes, policy=None):
    return Collector(
        excel=FakeExcel(),
        reader=FakeReader(quotes),
        clock=clock,
        chart_mode="NORMAL",
        enable_profit_rtd_order_flow=False,
        temporal_primary_policy=policy,
    )


def assert_buy_and_alert(pipeline, context, clock, capsys):
    capsys.readouterr()
    assert pipeline.executar(context) is context
    assert context.strategy.valid is True
    assert context.strategy.signal == "BUY"
    assert context.score.valid is True, context.score
    assert context.risk.valid is True
    assert context.risk.approved is True
    assert context.decision.valid is True
    assert context.decision.action == "BUY"
    assert context.alert.valid is True
    assert context.alert.action == "BUY"
    assert context.alert.timestamp == clock.current.strftime("%d/%m/%Y %H:%M:%S")
    assert "BUY" in capsys.readouterr().out


@pytest.mark.parametrize("event_offset", [-24, 24], ids=["antiga", "futura"])
def test_origin_time_is_replaced_and_quote_reaches_buy_and_alert(
    event_offset, offline_chain, capsys
):
    clock, pipeline = offline_chain
    event_time = NOW + timedelta(hours=event_offset)
    collector = collector_for(clock, quote(event_time))
    context = collector.get_data()

    assert context is not None
    assert context.market.timestamp == NOW != event_time
    assert context.market.candle_count == 1
    assert context.market.last_candle.timestamp == NOW
    assert context.market.last_candle.close == 180_000.0
    assert_buy_and_alert(pipeline, context, clock, capsys)


def test_regressive_event_is_reprocessed_in_reception_order(offline_chain, capsys):
    clock, pipeline = offline_chain
    t1 = NOW - timedelta(minutes=2)
    t2 = NOW - timedelta(minutes=1)
    prices = [180_000.0, 180_005.0, 180_010.0]
    collector = collector_for(
        clock, *(quote(event, price, 1000.0 + index)
                 for index, (event, price) in enumerate(zip((t1, t2, t1), prices)))
    )

    for index, price in enumerate(prices):
        clock.current = NOW + timedelta(minutes=index)
        context = collector.get_data()
        assert context is not None
        assert context.market.timestamp == clock.current
        assert context.market.last_price == price
        assert context.market.candle_count == index + 1
        assert_buy_and_alert(pipeline, context, clock, capsys)

    assert [c.timestamp for c in context.market.candles] == [
        NOW + timedelta(minutes=index) for index in range(3)
    ]
    assert [c.close for c in context.market.candles] == prices


def test_old_context_recomputes_operational_chain(offline_chain, capsys):
    clock, pipeline = offline_chain
    context = collector_for(clock, quote(NOW)).get_data()
    assert context is not None
    assert_buy_and_alert(pipeline, context, clock, capsys)
    first_alert_time = context.alert.timestamp

    # Remove os resultados para exigir que o próprio pipeline os recompute.
    context.clear_results()
    clock.current += timedelta(hours=24)
    assert_buy_and_alert(pipeline, context, clock, capsys)
    assert context.alert.timestamp != first_alert_time
    assert context.market.timestamp == NOW
    assert context.market.candle_count == 1


def test_frozen_payload_drops_auxiliary_and_receive_time_only_changes(
    offline_chain, capsys
):
    clock, pipeline = offline_chain
    original = quote(NOW)
    ignored_field_change = dict(original, strike=180_020.0)
    quote_time_change = dict(original, hora="10:01:00")
    collector = collector_for(
        clock, original, dict(original), ignored_field_change,
        dict(original), quote_time_change,
    )
    context = collector.get_data()
    assert context is not None
    assert_buy_and_alert(pipeline, context, clock, capsys)

    for index in range(1, 4):
        clock.current = NOW + timedelta(minutes=index)
        assert collector.get_data() is None
        assert context.market.timestamp == NOW
        assert context.market.candle_count == 1

    clock.current = NOW + timedelta(minutes=4)
    resumed = collector.get_data()
    assert resumed is not None
    assert resumed.market is context.market
    assert resumed.market.timestamp == clock.current
    assert resumed.market.candle_count == 2
    assert resumed.market.last_price == original["close"]
    assert_buy_and_alert(pipeline, resumed, clock, capsys)


PROTECTED_NOW = NOW.replace(tzinfo=timezone.utc)


@pytest.fixture
def protected_chain(offline_chain):
    clock, pipeline = offline_chain
    clock.current = PROTECTED_NOW
    pipeline.temporal_primary_policy = PRIMARY_QUOTE_TEMPORAL_POLICY
    pipeline.temporal_reference_provider = clock.now
    return clock, pipeline


@pytest.mark.parametrize(
    "offset,expected_reason",
    [
        (-31, "TEMPORAL_STALE_TIMESTAMP"),
        (3, "TEMPORAL_FUTURE_TIMESTAMP"),
    ],
)
def test_protected_collector_rejects_outside_source_time_window(
    protected_chain, capsys, offset, expected_reason
):
    clock, _ = protected_chain
    source_time = PROTECTED_NOW + timedelta(seconds=offset)
    collector = collector_for(clock, quote(source_time), policy=PRIMARY_QUOTE_TEMPORAL_POLICY)
    assert collector.get_data() is None
    assert collector.market.candle_count == 0
    assert collector.last_valid_volume is None
    assert expected_reason in capsys.readouterr().out


@pytest.mark.parametrize(
    "source_time,reason",
    [
        (None, "TEMPORAL_MISSING_TIMESTAMP"),
        ("corrupt", "TEMPORAL_INVALID_TIMESTAMP"),
        (NOW.isoformat(), "TEMPORAL_INVALID_TIMESTAMP"),
    ],
)
def test_protected_collector_and_pipeline_reject_missing_or_invalid_origin(
    protected_chain, capsys, source_time, reason
):
    clock, pipeline = protected_chain
    payload = dict(quote(PROTECTED_NOW), source_timestamp=source_time)
    collector = collector_for(clock, payload, policy=PRIMARY_QUOTE_TEMPORAL_POLICY)
    assert collector.get_data() is None
    assert reason in capsys.readouterr().out

    context = AnalysisContext(source_timestamp=source_time, received_timestamp=clock.current)
    assert pipeline.executar(context) is context
    assert context.decision.action == "WAIT"
    assert reason in context.decision.reasons
    assert not context.alert.valid


def test_regressive_quote_does_not_mutate_published_state(protected_chain, capsys):
    clock, pipeline = protected_chain
    t1 = PROTECTED_NOW - timedelta(seconds=4)
    t2 = PROTECTED_NOW - timedelta(seconds=3)
    first = dict(quote(t1), agressao_compra=10, agressao_venda=5)
    second = dict(quote(t2, 180_005.0, 1010), agressao_compra=20, agressao_venda=6)
    regressive = dict(quote(t1, 180_100.0, 9000), agressao_compra=700, agressao_venda=3)
    collector = collector_for(
        clock, first, second, regressive, second, policy=PRIMARY_QUOTE_TEMPORAL_POLICY
    )
    assert collector.get_data().source_timestamp == t1.isoformat()
    published = collector.get_data()
    assert published.source_timestamp == t2.isoformat()
    assert published.received_timestamp == PROTECTED_NOW
    assert_buy_and_alert(pipeline, published, clock, capsys)
    candle = published.market.last_candle
    candle_values = (candle.open, candle.high, candle.low, candle.close, candle.volume)
    flow = published.order_flow_state
    histories = {
        timeframe: tuple(collector.multi_timeframe.get(timeframe).candles)
        for timeframe in collector.multi_timeframe.TIMEFRAMES
    }

    assert collector.get_data() is None
    assert "TEMPORAL_REGRESSIVE_TIMESTAMP" in capsys.readouterr().out
    assert (candle.open, candle.high, candle.low, candle.close, candle.volume) == candle_values
    assert collector.market.last_price == 180_005.0
    assert collector.market.timestamp == PROTECTED_NOW
    assert collector.last_valid_volume == 1010
    assert (flow.cumulative_buy, flow.cumulative_sell) == (20, 6)
    assert collector._temporal_primary_history.previous(None, SYMBOL) == t2.isoformat()
    for timeframe, history in histories.items():
        assert tuple(collector.multi_timeframe.get(timeframe).candles) == history
    assert published.decision.action == "BUY"
    assert collector.get_data() is None  # A rejeição também preservou a deduplicação.


def test_new_event_with_same_price_and_volume_is_accepted(protected_chain, capsys):
    clock, pipeline = protected_chain
    t1 = PROTECTED_NOW - timedelta(seconds=1)
    first = dict(quote(t1), source_timestamp=t1.isoformat())
    second = dict(first, source_timestamp=PROTECTED_NOW.isoformat())
    collector = collector_for(
        clock, first, dict(first), second, policy=PRIMARY_QUOTE_TEMPORAL_POLICY
    )
    context = collector.get_data()
    assert context.source_timestamp == t1.isoformat()
    assert collector.get_data() is None
    new_context = collector.get_data()
    assert new_context.source_timestamp == PROTECTED_NOW.isoformat()
    assert new_context.market.last_price == 180_000.0
    assert new_context.market.volume == 1000.0
    assert_buy_and_alert(pipeline, new_context, clock, capsys)


def test_old_context_clears_previous_buy_and_skips_engines(protected_chain, capsys):
    clock, pipeline = protected_chain
    collector = collector_for(clock, quote(PROTECTED_NOW), policy=PRIMARY_QUOTE_TEMPORAL_POLICY)
    context = collector.get_data()
    assert_buy_and_alert(pipeline, context, clock, capsys)
    clock.current += timedelta(seconds=31)

    assert pipeline.executar(context) is context
    assert not context.strategy.valid
    assert not context.score.valid
    assert not context.risk.valid
    assert not context.decision.valid
    assert context.decision.action == "WAIT"
    assert "TEMPORAL_STALE_TIMESTAMP" in context.decision.reasons
    assert not context.alert.valid
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("clock_raises", [True, False])
def test_protected_paths_fail_closed_when_clock_fails(protected_chain, capsys, clock_raises):
    clock, pipeline = protected_chain

    def broken_now():
        if clock_raises:
            raise RuntimeError("clock offline")
        return NOW  # Sem fuso explícito.

    collector = collector_for(clock, quote(PROTECTED_NOW), policy=PRIMARY_QUOTE_TEMPORAL_POLICY)
    clock.now = broken_now
    pipeline.temporal_reference_provider = broken_now

    assert collector.get_data() is None
    assert collector.market.candle_count == 0
    assert "TEMPORAL_VALIDATION_ERROR" in capsys.readouterr().out
    context = AnalysisContext(source_timestamp=PROTECTED_NOW.isoformat())
    pipeline.executar(context)
    assert "TEMPORAL_VALIDATION_ERROR" in context.decision.reasons
    assert context.decision.action == "WAIT"
    assert not context.alert.valid


def test_legacy_pipeline_created_without_init_still_accepts_context():
    pipeline, _ = build_pipeline()
    context = AnalysisContext()
    assert pipeline.executar(context) is context
    assert "TEMPORAL_MISSING_TIMESTAMP" not in context.decision.reasons
