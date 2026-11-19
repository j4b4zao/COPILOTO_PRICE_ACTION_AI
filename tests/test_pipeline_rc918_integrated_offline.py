"""Integração offline da cotação RTD até a decisão e o alerta."""

from copy import deepcopy
from datetime import timedelta, timezone
from types import SimpleNamespace

import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from analysis.temporal_snapshot_policy import PRIMARY_QUOTE_TEMPORAL_POLICY as POLICY
from connectors.excel_connector import ExcelConnector
from connectors.profit_reader import ProfitReader
from core.analysis_context import AnalysisContext
from market_data.collector import Collector
from tests.test_pipeline_rc917_freshness_adversarial import (
    PROTECTED_NOW,
    assert_buy_and_alert,
    offline_chain,
    protected_chain,
)
from tests.test_trader_psychology_rc7 import build_pipeline


class OfflineWorkbook:
    def __init__(self):
        self.sheets = {ProfitReader.SHEET: self}
        self.rows = iter(())
        self.cells = {}
        self.block_reads = 0

    def publish(self, *rows):
        self.rows = iter(rows if len(rows) == 2 else rows * 2)
        self.cells = dict(zip((f"{column}2" for column in "ABCDEFGHIJKLMNOP"), rows[0]))

    def range(self, address):
        if address == "A2:P2":
            def options(*, ndim):
                assert ndim == 1
                self.block_reads += 1
                row = next(self.rows)
                if row is None:
                    raise OSError("simulated source outage")
                return SimpleNamespace(value=row)

            return SimpleNamespace(options=options)
        if address.endswith("1"):
            return SimpleNamespace(
                value=ProfitReader.EXPECTED_HEADERS[ProfitReader.HEADER_COLUMNS.index(address[0])]
            )
        return SimpleNamespace(value=self.cells[address])


def row(timestamp, *, price=180_000, volume=1000, symbol="WINZ26",
        expiry="16/12/2026", day=None):
    return [
        symbol, day or timestamp.date().isoformat(), timestamp.timetz().isoformat(),
        price, None, None, None, None, None, volume, expiry, None, None, None, None, None,
    ]


def make_collector(monkeypatch, clock, *, protected=True, source_timezone=None):
    workbook = OfflineWorkbook()
    excel = ExcelConnector()
    excel.book = workbook
    monkeypatch.setattr(excel, "conectar", lambda _path: True)
    options = {"temporal_primary_policy": POLICY} if protected else {}
    collector = Collector(
        excel=excel, clock=clock, chart_mode="RENKO", renko_brick_size=20,
        enable_profit_rtd_order_flow=False, source_timezone=source_timezone, **options,
    )
    assert isinstance(collector.reader, ProfitReader)
    return workbook, collector


def market_state(collector):
    markets = [collector.multi_timeframe.get(tf) for tf in ("M1", "M5", "M15")]
    markets.append(collector.renko.market)
    return deepcopy((
        [(m.symbol, m.timestamp, m.last_price, m.volume, list(m.candles)) for m in markets],
        collector.last_valid_volume, collector.last_new_candles,
        collector.last_closed_renko_bricks, collector.renko._current_open,
        collector.renko._last_cumulative_volume, collector.renko._brick_start_volume,
        collector._primary_contract, collector._last_primary_receipt,
        collector._temporal_primary_history._entries,
    ))


def assert_rejected(collector, pipeline, previous, reason, capsys):
    before = market_state(collector)
    history = list(pipeline._temporal_primary_history._entries)
    previous_results = deepcopy((previous.decision, previous.alert))
    capsys.readouterr()
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert reason in output
    assert "BUY" not in output and "SELL" not in output
    assert market_state(collector) == before
    assert pipeline.context is previous
    assert (previous.decision, previous.alert) == previous_results
    assert pipeline._temporal_primary_history._entries == history


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("naive", "TEMPORAL_SOURCE_TIMEZONE_REQUIRED"),
        ("old", "TEMPORAL_STALE_TIMESTAMP"),
        ("future", "TEMPORAL_FUTURE_TIMESTAMP"),
        ("regressive", "TEMPORAL_REGRESSIVE_TIMESTAMP"),
        ("receipt", "TEMPORAL_REGRESSIVE_RECEIPT"),
        ("WIN", "TEMPORAL_CONTRACT_TRANSITION_BLOCKED"),
        ("WDO", "TEMPORAL_CONTRACT_TRANSITION_BLOCKED"),
        ("mixed", "PROFIT_QUOTE_INCONSISTENT_READ"),
        ("outage", "PROFIT_QUOTE_READ_ERROR"),
        ("no_trades", "sem mudan"),
        ("closed", "TEMPORAL_STALE_TIMESTAMP"),
    ],
)
def test_rejection_preserves_published_chain(monkeypatch, protected_chain, capsys,
                                             scenario, reason):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    symbol = "WDOZ26" if scenario == "WDO" else "WINZ26"
    event = PROTECTED_NOW - timedelta(seconds=2)
    original = row(event, symbol=symbol)
    workbook.publish(original)
    first = collector.get_data()
    assert first.source_timestamp == event.isoformat()
    assert first.received_timestamp == clock.current
    assert_buy_and_alert(pipeline, first, clock, capsys)

    bad_time = {
        "naive": event.replace(tzinfo=None),
        "old": clock.current - timedelta(seconds=31),
        "future": clock.current + timedelta(seconds=3),
        "regressive": event - timedelta(seconds=1),
        "receipt": event + timedelta(seconds=1),
    }.get(scenario, event)
    bad = row(
        bad_time, symbol=symbol, price=190_000, volume=9999,
        expiry="17/02/2027" if scenario in {"WIN", "WDO"} else "16/12/2026",
    )
    if scenario == "receipt":
        clock.current -= timedelta(seconds=1)
    if scenario == "closed":
        clock.current = PROTECTED_NOW.replace(hour=22)
    if scenario == "mixed":
        workbook.publish(original, bad)
    elif scenario == "outage":
        workbook.rows = iter((None,))
    elif scenario in {"no_trades", "closed"}:
        workbook.publish(original)
    else:
        workbook.publish(bad)
    assert_rejected(collector, pipeline, first, reason, capsys)

    if scenario == "outage":
        clock.current += timedelta(seconds=1)
        workbook.publish(row(clock.current, price=180_040, volume=1010))
        resumed = collector.get_data()
        assert resumed.market.last_price == 180_040
        assert collector.last_closed_renko_bricks == 2
        assert collector.last_valid_volume == 1010
        assert_buy_and_alert(pipeline, resumed, clock, capsys)


def test_brazilian_date_and_stable_excel_snapshot(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    zone = timezone(timedelta(hours=-3))
    workbook, collector = make_collector(monkeypatch, clock, source_timezone=zone)
    local = clock.current.astimezone(zone)
    workbook.publish(row(local.replace(tzinfo=None), day=local.strftime("%d/%m/%Y")))
    context = collector.get_data()
    assert context.source_timestamp == local.isoformat()
    assert context.received_timestamp == clock.current
    assert workbook.block_reads == 2
    assert_buy_and_alert(pipeline, context, clock, capsys)


def test_reused_context_waits_and_distinct_context_same_second_passes(
    monkeypatch, protected_chain, capsys,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    workbook.publish(row(clock.current))
    first = collector.get_data()
    assert_buy_and_alert(pipeline, first, clock, capsys)
    before = market_state(collector)
    history = list(pipeline._temporal_primary_history._entries)
    assert pipeline.executar(first) is first
    assert first.decision.action == "WAIT"
    assert "TEMPORAL_CONTEXT_ALREADY_PROCESSED" in first.decision.reasons
    assert not first.alert.valid
    assert capsys.readouterr().out == ""
    assert market_state(collector) == before
    assert pipeline._temporal_primary_history._entries == history

    workbook.publish(row(clock.current, price=180_020, volume=1010))
    second = collector.get_data()
    assert second is not first
    assert second.source_timestamp == first.source_timestamp
    assert_buy_and_alert(pipeline, second, clock, capsys)


def test_m1_m5_m15_and_renko_form_from_same_ticks(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    for minute, price, volume in (
        (0, 180_000, 1000), (1, 180_040, 1010),
        (5, 180_060, 1030), (15, 180_080, 1060),
    ):
        clock.current = PROTECTED_NOW + timedelta(minutes=minute)
        workbook.publish(row(clock.current, price=price, volume=volume))
        context = collector.get_data()
        assert context.multi_timeframe is collector.multi_timeframe
        assert context.market is collector.renko.market
        assert_buy_and_alert(pipeline, context, clock, capsys)

    for tf, minutes, closes, volumes in (
        ("M1", (0, 1, 5, 15), (180_000, 180_040, 180_060, 180_080), (0, 10, 20, 30)),
        ("M5", (0, 5, 15), (180_040, 180_060, 180_080), (10, 20, 30)),
        ("M15", (0, 15), (180_060, 180_080), (30, 30)),
    ):
        candles = collector.multi_timeframe.get(tf).candles
        assert tuple(c.timestamp for c in candles) == tuple(
            PROTECTED_NOW + timedelta(minutes=minute) for minute in minutes
        )
        assert tuple(c.close for c in candles) == closes
        assert tuple(c.volume for c in candles) == volumes
    bricks = list(collector.renko.market.candles)
    assert [(c.open, c.close) for c in bricks] == [
        (180_000, 180_020), (180_020, 180_040), (180_040, 180_060),
        (180_060, 180_080), (180_080, 180_080),
    ]
    assert sum(c.volume for c in bricks) == 60


def test_legacy_defaults_and_pipeline_without_init(monkeypatch, offline_chain, capsys):
    clock, pipeline = offline_chain
    workbook, collector = make_collector(monkeypatch, clock, protected=False)
    assert collector.temporal_primary_policy is None
    assert AnalysisPipeline().temporal_primary_policy is None
    assert pipeline.temporal_primary_policy is None
    workbook.publish(row(clock.current - timedelta(days=1)))
    context = collector.get_data()
    assert workbook.block_reads == 0
    assert_buy_and_alert(pipeline, context, clock, capsys)
    assert_buy_and_alert(pipeline, context, clock, capsys)
    uninitialized, _ = build_pipeline()
    legacy_context = AnalysisContext()
    assert uninitialized.executar(legacy_context) is legacy_context
