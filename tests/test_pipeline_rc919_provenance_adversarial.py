"""Caracteriza os riscos R01 a R06 com dados exclusivamente sintéticos."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app import bot as bot_module
from core import connection_manager
from core.analysis_context import AnalysisContext
from tests.test_pipeline_rc917_freshness_adversarial import (
    PROTECTED_NOW,
    assert_buy_and_alert,
    offline_chain,
    protected_chain,
)
from tests.test_pipeline_rc918_integrated_offline import (
    assert_rejected,
    make_collector,
    market_state,
    row,
)


@pytest.mark.parametrize(
    "column,value",
    [
        (3, 180_040),
        (5, 180_090),
        (6, 179_910),
        (11, 42),
    ],
    ids=["ultimo", "maxima", "minima", "adx"],
)
def test_r01_duas_leituras(monkeypatch, protected_chain, capsys, column, value):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    original = row(clock.current)
    workbook.publish(original)
    published = collector.get_data()
    assert_buy_and_alert(pipeline, published, clock, capsys)

    clock.current += timedelta(seconds=1)
    first = row(clock.current, volume=1010)
    second = first.copy()
    second[column] = value
    workbook.publish(first, second)
    assert_rejected(collector, pipeline, published, "PROFIT_QUOTE_INCONSISTENT_READ", capsys)
    assert workbook.block_reads == 4


def test_r01_mistura_estavel_aceita_e_geracao_nao_determinavel(
    monkeypatch, protected_chain, capsys,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    before = row(clock.current - timedelta(seconds=1))
    after = row(clock.current, price=180_040, volume=1050)
    workbook.publish(before)
    assert_buy_and_alert(pipeline, collector.get_data(), clock, capsys)
    mixed = after.copy()
    mixed[3] = before[3]
    workbook.publish(mixed, mixed.copy())
    context = collector.get_data()
    assert context.source_timestamp == clock.current.isoformat()
    assert context.market.last_price == before[3] != after[3]
    assert context.market.last_candle.volume == 50
    assert workbook.block_reads == 4
    assert_buy_and_alert(pipeline, context, clock, capsys)


@pytest.mark.parametrize(
    "scenario,diagnostic",
    [
        ("available", None),
        ("excel_unavailable", "PROFIT_QUOTE_READ_ERROR"),
        ("read_error", "PROFIT_QUOTE_READ_ERROR"),
        ("frozen", "sem mudan"),
        ("no_trades", "sem mudan"),
        ("closed", "TEMPORAL_STALE_TIMESTAMP"),
    ],
)
def test_r02_atividade_do_loop_nao_mede_saude_da_fonte(
    monkeypatch, protected_chain, capsys, scenario, diagnostic,
):
    clock, pipeline = protected_chain
    monkeypatch.setattr(connection_manager, "datetime", clock)
    workbook, collector = make_collector(monkeypatch, clock)
    original = row(clock.current)
    workbook.publish(original)
    published = collector.get_data()
    assert_buy_and_alert(pipeline, published, clock, capsys)
    previous = market_state(collector)
    prior_results = deepcopy((published.decision, published.alert))
    clock.current += timedelta(seconds=1)
    if scenario == "closed":
        clock.current = clock.current.replace(hour=22)
    if scenario == "excel_unavailable":
        collector.excel.book = None
    elif scenario == "read_error":
        workbook.rows = iter((None,))
    elif scenario == "available":
        workbook.publish(row(clock.current, price=180_040, volume=1010))
    else:
        workbook.publish(original)

    bot = object.__new__(bot_module.Bot)
    bot.connection = connection_manager.ConnectionManager()
    bot.collector = collector
    bot.pipeline = pipeline
    log = []
    bot.logger = SimpleNamespace(info=log.append, warning=log.append, erro=log.append)
    shown = []
    bot.mostrar = shown.append

    def end_after_cycle(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(bot_module, "time", SimpleNamespace(sleep=end_after_cycle))
    assert bot.connection.verificar()["status"] == "SEM_DADOS"
    capsys.readouterr()
    bot.executar()
    assert bot.connection.verificar()["status"] == "ATIVA"
    assert bot.connection.ultima_atualizacao == clock.current
    captured = capsys.readouterr()
    assert captured.err.splitlines() == ["[DATA LOOP] PROFIT_LOOP_ACTIVE"]
    output = captured.out
    if diagnostic is None:
        assert len(shown) == 1
        context = shown[0]
        assert isinstance(context, AnalysisContext) and context is not published
        assert context.decision.valid and context.decision.action == "BUY"
        assert context.alert.valid and context.alert.action == "BUY"
        assert "BUY" in output
        assert "PROFIT_QUOTE_READ_OK" in output
        assert "PROFIT_QUOTE_ACCEPTED" in output
    else:
        assert diagnostic in output
        assert "[DATA REJECTED]" in output
        assert "PROFIT_QUOTE_ACCEPTED" not in output
        assert not shown
        assert "Aguardando dados do mercado..." in log
        assert market_state(collector) == previous
        assert pipeline.context is published
        assert (published.decision, published.alert) == prior_results
        assert "BUY" not in output and "SELL" not in output


@pytest.mark.parametrize(
    "seconds,counts",
    [(20, (1, 1, 1)), (125, (2, 1, 1)), (370, (2, 2, 1)), (960, (2, 2, 2))],
    ids=["dentro-M1", "atravessa-M1", "atravessa-M5", "atravessa-M15"],
)
def test_r03_lacuna_retomada_volume_renko_e_fluxo(
    monkeypatch, protected_chain, capsys, seconds, counts,
):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    original = row(clock.current)
    original[14:] = [800, 200]
    workbook.publish(original)
    assert collector.get_data() is not None

    clock.current += timedelta(seconds=seconds)
    before = market_state(collector)
    workbook.rows = iter((None,))
    assert collector.get_data() is None
    assert market_state(collector) == before

    resumed = row(clock.current, price=180_060, volume=1300)
    resumed[14:] = [1020, 280]
    workbook.publish(resumed)
    context = collector.get_data()
    assert "PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE" in capsys.readouterr().out
    assert context.source_timestamp == clock.current.isoformat()
    assert context.received_timestamp == clock.current
    for minutes, count in zip((1, 5, 15), counts):
        market = collector.multi_timeframe.get(f"M{minutes}")
        bucket = clock.current.replace(minute=clock.current.minute // minutes * minutes, second=0)
        timestamps = [PROTECTED_NOW] if count == 1 else [PROTECTED_NOW, bucket]
        assert [c.timestamp for c in market.candles] == timestamps
        assert market.last_candle.close == 180_060
        assert market.last_candle.volume == 0
    bricks = list(collector.renko.market.candles)
    assert [b.close for b in bricks] == [180_020, 180_040, 180_060, 180_060]
    assert [b.timestamp for b in bricks] == [clock.current] * 4
    assert [b.volume for b in bricks] == [0, 0, 0, 0]
    assert collector.last_closed_renko_bricks == 3
    assert collector.order_flow.source_units == 0
    assert not collector.order_flow.history

    clock.current += timedelta(seconds=1)
    next_row = row(clock.current, price=180_080, volume=1310)
    next_row[14:] = [1028, 282]
    workbook.publish(next_row)
    assert collector.get_data() is not None
    assert all(collector.multi_timeframe.get(tf).last_candle.volume == 10
               for tf in ("M1", "M5", "M15"))
    assert sum(brick.volume for brick in collector.renko.market.candles) == 10
    assert list(collector.order_flow.history) == [6]

    clock.current += timedelta(seconds=1)
    reset = row(clock.current, price=180_100, volume=25)
    reset[14:] = [20, 5]
    workbook.publish(reset)
    assert collector.get_data() is not None
    assert collector.last_valid_volume == 25
    assert all(collector.multi_timeframe.get(tf).last_candle.volume == 0
               for tf in ("M1", "M5", "M15"))
    assert sum(brick.volume for brick in collector.renko.market.candles) == 10
    assert collector.order_flow.cumulative_buy == 20
    assert not collector.order_flow.ready and not collector.order_flow.history


@pytest.mark.parametrize("evidence", ["missing_volume", "source_gap", "receipt_gap"])
def test_r03_lacuna_preserva_volume_atribuido(monkeypatch, protected_chain, capsys, evidence):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    origin_lag = timedelta(seconds=10 if evidence == "source_gap" else 0)
    workbook.publish(row(clock.current - origin_lag))
    assert collector.get_data() is not None
    clock.current += timedelta(seconds=1)
    workbook.publish(row(clock.current - origin_lag, price=180_005, volume=1010))
    assert collector.get_data() is not None
    capsys.readouterr()

    if evidence == "missing_volume":
        clock.current += timedelta(seconds=1)
        workbook.publish(row(clock.current, price=180_007, volume=None))
        before = market_state(collector)
        assert collector.get_data() is None
        assert market_state(collector) == before
        assert "PROFIT_QUOTE_INVALID_VOLUME" in capsys.readouterr().out
        clock.current += timedelta(seconds=1)
        event = clock.current
    elif evidence == "source_gap":
        clock.current += timedelta(seconds=25)
        event = clock.current
    else:
        clock.current += timedelta(seconds=31)
        event = clock.current - timedelta(seconds=2)

    workbook.publish(row(event, price=180_010, volume=1500))
    assert collector.get_data() is not None
    assert "PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE" in capsys.readouterr().out
    for tf in ("M1", "M5", "M15"):
        assert collector.multi_timeframe.get(tf).last_candle.volume == 10
    assert collector.renko.market.last_candle.volume == 10


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("naive_receipt", "TEMPORAL_VALIDATION_ERROR"),
        ("explicit_offset", None),
        ("naive_origin", "TEMPORAL_SOURCE_TIMEZONE_REQUIRED"),
        ("explicit_zone", None),
        ("receipt_regression", "TEMPORAL_REGRESSIVE_RECEIPT"),
        ("future", "TEMPORAL_FUTURE_TIMESTAMP"),
        ("old", "TEMPORAL_STALE_TIMESTAMP"),
        ("ambiguous", "TEMPORAL_INVALID_TIMESTAMP"),
        ("nonexistent", "TEMPORAL_INVALID_TIMESTAMP"),
    ],
)
def test_r04_relogios_e_contrato_temporal(monkeypatch, protected_chain, capsys, scenario, reason):
    clock, pipeline = protected_chain
    zone = None
    if scenario == "explicit_zone":
        zone = timezone(timedelta(hours=5, minutes=30))
    elif scenario in {"ambiguous", "nonexistent"}:
        zone = ZoneInfo("America/New_York")
    workbook, collector = make_collector(monkeypatch, clock, source_timezone=zone)
    seed = clock.current - timedelta(seconds=3)
    workbook.publish(row(seed))
    published = collector.get_data()
    assert_buy_and_alert(pipeline, published, clock, capsys)
    origin = clock.current
    if scenario == "naive_receipt":
        clock.current = clock.current.replace(tzinfo=None)
    elif scenario in {"naive_origin", "explicit_zone"}:
        origin = origin.astimezone(zone or timezone.utc).replace(tzinfo=None)
    elif scenario == "explicit_offset":
        clock.current = clock.current.astimezone(timezone(timedelta(hours=2)))
        origin = clock.current
    elif scenario == "receipt_regression":
        clock.current -= timedelta(seconds=1)
    elif scenario == "future":
        origin += timedelta(seconds=3)
    elif scenario == "old":
        origin -= timedelta(seconds=31)
    elif scenario == "ambiguous":
        origin = datetime(2026, 11, 1, 1, 30)
    elif scenario == "nonexistent":
        origin = datetime(2026, 3, 8, 2, 30)

    workbook.publish(row(origin, price=180_040, volume=1010))
    if reason:
        assert_rejected(collector, pipeline, published, reason, capsys)
    else:
        context = collector.get_data()
        expected = origin.replace(tzinfo=zone) if zone else origin
        assert context.source_timestamp == expected.isoformat()
        assert context.received_timestamp.isoformat() == clock.current.isoformat()
        assert_buy_and_alert(pipeline, context, clock, capsys)


@pytest.mark.parametrize("protected", [False, True], ids=["desativada", "ativada"])
@pytest.mark.parametrize("prefix", ["WIN", "WDO"])
@pytest.mark.parametrize("change", ["expiry", "symbol", "both"])
def test_r05_rollover_e_deduplicacao(monkeypatch, protected_chain, capsys, protected, prefix, change):
    clock, pipeline = protected_chain
    if not protected:
        pipeline.temporal_primary_policy = None
    workbook, collector = make_collector(monkeypatch, clock, protected=protected)
    symbol = prefix + "Z26"
    expiry = "16/12/2026"
    original = row(clock.current, symbol=symbol, expiry=expiry)
    original[14:] = [800, 200]
    workbook.publish(original)
    published = collector.get_data()
    assert_buy_and_alert(pipeline, published, clock, capsys)
    previous = market_state(collector)
    change_row = original.copy()
    if change in {"symbol", "both"}:
        change_row[0] = prefix + "G27"
    if change in {"expiry", "both"}:
        change_row[10] = "17/02/2027"
    workbook.publish(change_row)
    if protected:
        flow = deepcopy(collector.order_flow)
        fingerprint = collector.source_guard._last_fingerprint
        assert_rejected(
            collector, pipeline, published, "TEMPORAL_CONTRACT_TRANSITION_BLOCKED", capsys,
        )
        assert collector.order_flow == flow
        assert collector.source_guard._last_fingerprint == fingerprint
        return

    changed = collector.get_data()
    if change == "expiry":
        assert changed is None
        assert market_state(collector) == previous
    else:
        assert changed.market.symbol == change_row[0]
    change_row[3], change_row[9] = 180_040, 1100
    change_row[14:] = [860, 240]
    workbook.publish(change_row)
    changed = collector.get_data()
    assert changed.market.symbol == change_row[0]
    assert changed.market.candles[0].open == 180_000
    assert collector.last_closed_renko_bricks == 2
    for tf in ("M1", "M5", "M15"):
        market = collector.multi_timeframe.get(tf)
        assert market.candle_count == 1
        assert (market.last_candle.open, market.last_candle.close, market.last_candle.volume) == (
            180_000, 180_040, 100,
        )
    assert collector.last_valid_volume == 1100
    assert collector.order_flow.cumulative_buy == 860
    assert list(collector.order_flow.history) == [20]
    assert len(collector._temporal_primary_history) == 0
    workbook.publish(change_row)
    before_duplicate = market_state(collector)
    assert collector.get_data() is None
    assert market_state(collector) == before_duplicate


@pytest.mark.parametrize("day_meaning", ["negociacao", "atualizacao"])
@pytest.mark.parametrize("hour_meaning", ["ultimo_negocio", "cotacao", "atualizacao"])
def test_r06_semantica_nao_comprovada(
    monkeypatch, protected_chain, capsys, day_meaning, hour_meaning,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    # Os rótulos são hipóteses do teste, ausentes da linha entregue ao leitor.
    hypothetical = SimpleNamespace(
        day_meaning=day_meaning, hour_meaning=hour_meaning,
        values=row(clock.current, day=clock.current.strftime("%d/%m/%Y")),
    )
    workbook.publish(hypothetical.values)
    context = collector.get_data()
    assert context.source_timestamp == PROTECTED_NOW.isoformat()
    assert context.received_timestamp == PROTECTED_NOW
    assert_buy_and_alert(pipeline, context, clock, capsys)
