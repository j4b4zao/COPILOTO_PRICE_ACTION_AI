"""Caracterização offline do contrato temporal Profit na RC9.17."""

from datetime import datetime, timedelta, timezone

import pytest

from analysis.temporal_snapshot_policy import PRIMARY_QUOTE_TEMPORAL_POLICY as POLICY
from connectors.profit_reader import ProfitReader
from core.analysis_context import AnalysisContext
from market_data.collector import Collector
from tests.test_collector_multi_timeframe_rc31 import FakeExcel, FakeReader
from tests.test_pipeline_rc917_freshness_adversarial import (
    PROTECTED_NOW,
    assert_buy_and_alert,
    collector_for,
    offline_chain,
    protected_chain,
    quote,
)
from tests.test_profit_rtd_rc2 import Excel
from tests.test_trader_psychology_rc7 import build_pipeline


def assert_guard_rejection(collector, reason, capsys):
    capsys.readouterr()
    assert collector.get_data() is None
    assert reason in capsys.readouterr().out


@pytest.mark.parametrize(
    "day,hour,reason",
    [
        ("16/10/2026", "18:24:59", "TEMPORAL_SOURCE_TIMEZONE_REQUIRED"),
        ("31/02/2026", "18:24:59", "TEMPORAL_INVALID_TIMESTAMP"),
        ("2026-10-16", "25:00:00+00:00", "TEMPORAL_INVALID_TIMESTAMP"),
        ("", "18:24:59", "TEMPORAL_MISSING_TIMESTAMP"),
        ("2026-10-16", None, "TEMPORAL_MISSING_TIMESTAMP"),
        ("2026-10-16", "18:24:59", "TEMPORAL_SOURCE_TIMEZONE_REQUIRED"),
    ],
)
def test_profit_date_and_time_without_compatible_origin(
    protected_chain, capsys, day, hour, reason
):
    clock, _ = protected_chain
    clock.current = datetime(2026, 10, 16, 18, 25, tzinfo=timezone.utc)
    excel = Excel()
    excel.values.update(B2=day, C2=hour)
    collector = Collector(
        excel=FakeExcel(), reader=ProfitReader(excel), clock=clock,
        chart_mode="NORMAL", enable_profit_rtd_order_flow=False,
        temporal_primary_policy=POLICY,
    )
    assert_guard_rejection(collector, reason, capsys)
    assert collector.market.candle_count == 0
    assert collector.last_valid_volume is None


def test_brazilian_profit_date_uses_only_injected_timezone(protected_chain, capsys):
    clock, pipeline = protected_chain
    zone = timezone(timedelta(hours=-3))  # Contrato sintético desta fixture.
    clock.current = datetime(2026, 10, 16, 21, 25, tzinfo=timezone.utc)
    excel = Excel()
    excel.values.update(B2="16/10/2026", C2="18:24:59")
    collector = Collector(
        excel=FakeExcel(), reader=ProfitReader(excel), clock=clock,
        chart_mode="NORMAL", enable_profit_rtd_order_flow=False,
        temporal_primary_policy=POLICY, source_timezone=zone,
    )
    context = collector.get_data()
    assert context.source_timestamp == "2026-10-16T18:24:59-03:00"
    assert context.received_timestamp == clock.current
    assert_buy_and_alert(pipeline, context, clock, capsys)


@pytest.mark.parametrize("clock_kind", ["naive", "offset", "exception", "wrong_type"])
def test_reference_clock_contract(protected_chain, capsys, clock_kind):
    clock, _ = protected_chain

    def now():
        if clock_kind == "exception":
            raise RuntimeError("relógio indisponível")
        return {
            "naive": PROTECTED_NOW.replace(tzinfo=None),
            "offset": PROTECTED_NOW.astimezone(timezone(timedelta(hours=-3))),
            "wrong_type": PROTECTED_NOW.isoformat(),
        }[clock_kind]

    clock.now = now
    collector = collector_for(clock, quote(PROTECTED_NOW), policy=POLICY)
    if clock_kind == "offset":
        context = collector.get_data()
        assert context is not None
        assert context.received_timestamp.isoformat().endswith("-03:00")
        assert context.source_timestamp == PROTECTED_NOW.isoformat()
    else:
        assert_guard_rejection(collector, "TEMPORAL_VALIDATION_ERROR", capsys)
        assert collector.market.candle_count == 0
        assert collector.last_valid_volume is None


@pytest.mark.parametrize(
    "offset,reason",
    [(-29, None), (-30, None), (-31, "STALE"), (1, None), (2, None), (3, "FUTURE")],
)
def test_temporal_boundaries_are_inclusive(protected_chain, capsys, offset, reason):
    clock, _ = protected_chain
    event = PROTECTED_NOW + timedelta(seconds=offset)
    collector = collector_for(clock, quote(event), policy=POLICY)
    if reason is None:
        context = collector.get_data()
        assert context.source_timestamp == event.isoformat()
        assert context.market.candle_count == 1
    else:
        assert_guard_rejection(collector, f"TEMPORAL_{reason}_TIMESTAMP", capsys)
        assert collector.market.candle_count == 0


def test_regression_is_rejected_but_distinct_events_at_same_second_pass(
    protected_chain, capsys
):
    clock, pipeline = protected_chain
    t1 = PROTECTED_NOW - timedelta(seconds=2)
    t2 = PROTECTED_NOW - timedelta(seconds=1)
    collector = collector_for(
        clock, quote(t1), quote(t2, 180_010, 1010), quote(t1, 190_000, 9999),
        quote(t2, 180_020, 1020), policy=POLICY,
    )
    first = collector.get_data()
    assert first.source_timestamp == t1.isoformat()
    assert_buy_and_alert(pipeline, first, clock, capsys)
    second = collector.get_data()
    assert second.source_timestamp == t2.isoformat()
    assert_buy_and_alert(pipeline, second, clock, capsys)

    assert_guard_rejection(collector, "TEMPORAL_REGRESSIVE_TIMESTAMP", capsys)
    assert collector._temporal_primary_history.previous(None, second.market.symbol) == t2.isoformat()
    assert second.market.last_price == 180_010
    assert second.market.candle_count == 1
    assert second.market.last_candle.close == 180_010
    assert second.market.last_candle.volume == 10
    assert collector.last_valid_volume == 1010

    distinct = collector.get_data()
    assert distinct.source_timestamp == t2.isoformat()
    assert distinct.market.last_candle.close == 180_020
    assert_buy_and_alert(pipeline, distinct, clock, capsys)


@pytest.mark.parametrize("protected", [True, False])
def test_same_symbol_rollover_does_not_mix_protected_state(protected_chain, capsys, protected):
    clock, _ = protected_chain
    t1 = PROTECTED_NOW - timedelta(seconds=1)
    original = dict(quote(PROTECTED_NOW), vencimento="16/12/2026")
    rollover = dict(original, vencimento="17/02/2027")
    collector = collector_for(
        clock, original, rollover, dict(rollover, source_timestamp=t1.isoformat()),
        dict(rollover, close=180_030, volume=1060), policy=POLICY if protected else None,
    )
    first = collector.get_data()
    markets = [collector.multi_timeframe.get(tf) for tf in ("M1", "M5", "M15")]
    candles = [market.last_candle for market in markets]
    assert_guard_rejection(
        collector, "TEMPORAL_CONTRACT_TRANSITION_BLOCKED" if protected else "sem mudan", capsys
    )
    if not protected:
        assert collector.get_data() is None  # Campo explícito fica fora do guard legado.
        assert collector.get_data() is not None
        assert collector.last_valid_volume == 1060
        assert all(candle.volume == 60 for candle in candles)
        return
    assert_guard_rejection(collector, "TEMPORAL_REGRESSIVE_TIMESTAMP", capsys)
    assert_guard_rejection(collector, "TEMPORAL_CONTRACT_TRANSITION_BLOCKED", capsys)
    assert first.source_timestamp == PROTECTED_NOW.isoformat()
    assert collector.last_valid_volume == 1000
    for market, candle in zip(markets, candles):
        assert market.candle_count == 1
        assert market.last_candle is candle
        assert (candle.open, candle.close, candle.volume) == (180_000, 180_000, 0)


@pytest.mark.parametrize("chart_mode", ["NORMAL", "RENKO"])
def test_increasing_origin_with_reception_reversal_is_blocked(protected_chain, capsys, chart_mode):
    clock, _ = protected_chain
    events = [PROTECTED_NOW - timedelta(seconds=s) for s in (5, 4, 3)]
    receptions = [PROTECTED_NOW, PROTECTED_NOW - timedelta(seconds=1), PROTECTED_NOW]
    reader = FakeReader([quote(event, 180_000 + i * 40, 1000 + i * 10)
                         for i, event in enumerate(events)])
    collector = Collector(
        excel=FakeExcel(), reader=reader, clock=clock, chart_mode=chart_mode,
        renko_brick_size=20, enable_profit_rtd_order_flow=False,
        temporal_primary_policy=POLICY,
    )
    for index, (event, receipt) in enumerate(zip(events, receptions)):
        clock.current = receipt
        if index == 1:
            assert_guard_rejection(collector, "TEMPORAL_REGRESSIVE_RECEIPT", capsys)
            assert collector.last_valid_volume == 1000
            assert context.market.last_price == 180_000
            assert context.market.candle_count == 1
            continue
        context = collector.get_data()
        assert context.source_timestamp == event.isoformat()
        assert context.received_timestamp == receipt
        assert context.market.timestamp == receipt
        if chart_mode == "RENKO":
            assert context.market.last_candle.timestamp == receipt

    for minutes in (1, 5, 15):
        stamps = [c.timestamp for c in collector.multi_timeframe.get(f"M{minutes}").candles]
        assert stamps == [PROTECTED_NOW]

    if chart_mode == "RENKO":
        stamps = [c.timestamp for c in context.market.candles]
        assert len(stamps) == 5
        assert stamps == [PROTECTED_NOW] * 5
        assert context.market.last_candle.close == 180_080


@pytest.mark.parametrize("old_hour", [True, False])
def test_cellwise_midnight_read_combines_generations(protected_chain, capsys, old_hour):
    clock, _ = protected_chain
    clock.current = datetime(2026, 11, 19, 0, 0, 2, tzinfo=timezone.utc)
    excel = Excel()
    before = {"B2": "2026-11-18", "C2": "23:59:59+00:00", "D2": 180_000,
              "J2": 1000, "K2": "16/12/2026"}
    after = {"B2": "2026-11-19", "C2": "00:00:01+00:00", "D2": 180_050,
             "J2": 3000, "K2": "17/02/2027"}

    class InterleavedExcel:
        def ler_celula(self, sheet, cell):
            if cell in ("D2", "K2") or (cell == "C2" and old_hour):
                return before[cell]
            if cell in after:
                return after[cell]
            return excel.ler_celula(sheet, cell)

    reader = ProfitReader(InterleavedExcel())
    mixed = reader.obter_dados()
    assert tuple(mixed[key] for key in ("data", "hora", "close", "volume", "vencimento")) == (
        "2026-11-19", "23:59:59+00:00" if old_hour else "00:00:01+00:00",
        180_000, 3000, "16/12/2026",
    )
    collector = Collector(
        excel=FakeExcel(), reader=reader, clock=clock, chart_mode="NORMAL",
        enable_profit_rtd_order_flow=False, temporal_primary_policy=POLICY,
    )
    if old_hour:
        assert_guard_rejection(collector, "TEMPORAL_FUTURE_TIMESTAMP", capsys)
    else:
        context = collector.get_data()
        assert context.source_timestamp == "2026-11-19T00:00:01+00:00"
        assert context.market.last_price == 180_000
        assert context.market.volume == 3000


def test_direct_context_same_timestamp_repeats_then_expires(protected_chain, capsys):
    clock, pipeline = protected_chain
    context = AnalysisContext(source_timestamp=PROTECTED_NOW.isoformat())
    context.market.symbol = "WINZ26"
    context.market.last_price = 180_000
    assert_buy_and_alert(pipeline, context, clock, capsys)

    clock.current += timedelta(seconds=29)
    assert pipeline.executar(context) is context
    assert context.decision.action == "WAIT"
    assert "TEMPORAL_CONTEXT_ALREADY_PROCESSED" in context.decision.reasons
    assert not context.alert.valid
    assert capsys.readouterr().out == ""
    clock.current += timedelta(seconds=2)
    assert pipeline.executar(context) is context
    assert context.decision.action == "WAIT"
    assert "TEMPORAL_STALE_TIMESTAMP" in context.decision.reasons
    assert not context.alert.valid
    assert capsys.readouterr().out == ""

    context.source_timestamp = clock.current.isoformat()
    assert pipeline.executar(context) is context
    assert "TEMPORAL_CONTEXT_ALREADY_PROCESSED" in context.decision.reasons
    assert not context.alert.valid
    fresh = AnalysisContext(market=context.market, source_timestamp=context.source_timestamp)
    assert_buy_and_alert(pipeline, fresh, clock, capsys)
    distinct = AnalysisContext(market=context.market, source_timestamp=context.source_timestamp)
    assert_buy_and_alert(pipeline, distinct, clock, capsys)


def test_block_reader_rejects_observable_rtd_generation_change(protected_chain, capsys):
    clock, _ = protected_chain
    excel = Excel()
    old = ["WINZ26", "2026-11-18", "09:59:59+00:00", 180_000, *([None] * 5),
           1000, "16/12/2026", *([None] * 5)]
    new = old.copy()
    new[2] = "10:00:00+00:00"
    new[3] = 180_050
    new[9] = 1010
    rows = iter((old, new, new, new))
    reads = []

    def read_range(sheet, address):
        reads.append((sheet, address))
        return next(rows)

    excel.ler_intervalo = read_range
    collector = Collector(
        excel=FakeExcel(), reader=ProfitReader(excel), clock=clock,
        chart_mode="NORMAL", enable_profit_rtd_order_flow=False,
        temporal_primary_policy=POLICY,
    )
    assert_guard_rejection(collector, "PROFIT_QUOTE_INCONSISTENT_READ", capsys)
    assert collector.market.candle_count == 0
    assert collector.last_valid_volume is None
    context = collector.get_data()
    assert context.market.last_price == 180_050
    assert reads == [("Planilha1", "A2:P2")] * 4


def test_legacy_object_without_init_keeps_legacy_contract():
    pipeline, _ = build_pipeline()
    context = AnalysisContext()
    assert pipeline.executar(context) is context


@pytest.mark.parametrize("scenario", ["unavailable", "frozen", "closed", "no_trades"])
def test_silence_has_no_transport_or_session_classification(
    protected_chain, capsys, scenario
):
    clock, _ = protected_chain
    fresh = quote(PROTECTED_NOW)
    if scenario == "closed":
        clock.current = PROTECTED_NOW.replace(hour=20)
    elif scenario == "no_trades":
        clock.current += timedelta(seconds=31)
    payloads = {
        "unavailable": (None,),
        "frozen": (fresh, dict(fresh)),
        "closed": (fresh,),
        "no_trades": (fresh,),
    }
    collector = collector_for(clock, *payloads[scenario], policy=POLICY)
    if scenario == "frozen":
        assert collector.get_data() is not None
        assert_guard_rejection(collector, "sem mudan", capsys)
        assert collector.market.candle_count == 1
    elif scenario == "unavailable":
        assert collector.get_data() is None
        assert capsys.readouterr().out == "[DATA REJECTED] PROFIT_QUOTE_UNAVAILABLE\n"
    else:
        assert_guard_rejection(collector, "TEMPORAL_STALE_TIMESTAMP", capsys)
        assert collector.market.candle_count == 0
