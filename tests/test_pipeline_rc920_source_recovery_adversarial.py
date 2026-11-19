"""Caracterização offline da saúde observável e da retomada da fonte."""

from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import bot as bot_module
from core import connection_manager
from market_data.profit_rtd_order_flow_pipeline import ProfitRTDOrderFlowPipeline
from tests.test_pipeline_rc917_freshness_adversarial import (
    assert_buy_and_alert,
    offline_chain,
    protected_chain,
)
from tests.test_pipeline_rc918_integrated_offline import make_collector, market_state, row


def quote(clock, **values):
    tick = row(clock.current, **values)
    tick[14:] = [800, 200]
    return tick


@pytest.mark.parametrize("failure_stage", ["leitura", "apos_deduplicacao_auxiliar"])
def test_r03_falha_auxiliar_preserva_estado_e_permite_repetir(
    monkeypatch, protected_chain, capsys, failure_stage,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    fail_read = False

    def read_times_trades(symbol):
        if fail_read and failure_stage == "leitura":
            raise OSError("falha RTD sintética após início do rebase")
        return {
            "symbol": symbol, "timestamp": clock.current.isoformat(),
            "observational_only": True,
            "trades": [{
                "timestamp": clock.current.isoformat(), "buyer": "A", "seller": "B",
                "price": 180_000, "quantity": 1, "aggressor": "Comprador",
            }],
        }

    rtd = ProfitRTDOrderFlowPipeline(SimpleNamespace(read_times_trades=read_times_trades),
                                        collector.order_flow)
    build = rtd.aggression_builder.build

    def build_aggression(batch):
        if fail_read and failure_stage == "apos_deduplicacao_auxiliar":
            raise OSError("falha RTD sintética após deduplicação")
        return build(batch)

    rtd.aggression_builder = SimpleNamespace(build=build_aggression)
    collector.enable_profit_rtd_order_flow = True
    collector.profit_rtd_order_flow_pipeline = rtd
    workbook.publish(quote(clock))
    original = collector.get_data()
    assert_buy_and_alert(pipeline, original, clock, capsys)
    before = market_state(collector)
    fingerprint = collector.source_guard._last_fingerprint
    history = list(pipeline._temporal_primary_history._entries)
    results = deepcopy((original.decision, original.alert))
    assert collector.order_flow.cumulative_buy == 0
    assert rtd.deduplicator._previous
    flow = deepcopy(collector.order_flow)
    trades_signature = rtd.deduplicator._previous
    receipt = collector.last_profit_rtd_receipt
    recorder = collector.profit_rtd_validation_summary()

    clock.current += timedelta(seconds=31)
    resumed = quote(clock, price=180_060, volume=1400)
    workbook.publish(resumed)
    fail_read = True
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert "PROFIT_LOCAL_RECOVERY_COMPLETE" not in output
    assert "BUY" not in output and "SELL" not in output
    assert collector._primary_gap_pending
    assert market_state(collector) == before
    assert collector._primary_chart_volume == 1000
    assert collector.source_guard._last_fingerprint == fingerprint
    assert collector.order_flow == flow
    assert original.order_flow_state is collector.order_flow
    assert rtd.deduplicator._previous == trades_signature
    assert collector.last_profit_rtd_receipt is receipt
    assert collector.profit_rtd_validation_summary() == recorder
    assert pipeline.context is original
    assert pipeline._temporal_primary_history._entries == history
    assert (original.decision, original.alert) == results

    fail_read = False
    workbook.publish(resumed)
    recovered = collector.get_data()
    assert recovered is not original
    assert recovered is not None
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_PUBLISHED" in output
    assert "PROFIT_LOCAL_RECOVERY_COMPLETE reason=PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert collector.source_guard._last_fingerprint != fingerprint
    assert not collector._primary_gap_pending
    assert collector.last_valid_volume == 1400
    assert collector._primary_chart_volume == 1000
    assert collector.last_closed_renko_bricks == 3
    assert sum(c.volume for c in recovered.market.candles) == 0
    assert collector.last_profit_rtd_receipt.baseline_reset
    assert not collector.order_flow.history
    assert_buy_and_alert(pipeline, recovered, clock, capsys)


def test_r03_falha_de_publicacao_exige_novo_coletor(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    workbook.publish(quote(clock))
    original = collector.get_data()
    assert_buy_and_alert(pipeline, original, clock, capsys)
    signature = collector.source_guard._last_fingerprint
    clock.current += timedelta(seconds=1)
    next_tick = quote(clock, price=180_040, volume=1100)
    workbook.publish(next_tick)
    monkeypatch.setattr(collector.renko, "update_tick", Mock(side_effect=RuntimeError("Renko")))

    with pytest.raises(RuntimeError, match="Renko"):
        collector.get_data()
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert "PROFIT_LOCAL_RECOVERY_COMPLETE" not in output
    assert collector.source_guard._last_fingerprint == signature
    assert pipeline.context is original

    partial = market_state(collector)
    workbook.publish(next_tick)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_REINITIALIZATION_REQUIRED" in capsys.readouterr().out
    assert market_state(collector) == partial

    replacement_workbook, replacement = make_collector(monkeypatch, clock)
    replacement_workbook.publish(next_tick)
    recovered = replacement.get_data()
    assert recovered is not None and recovered is not original
    assert recovered.market.last_candle.volume == 0
    assert_buy_and_alert(pipeline, recovered, clock, capsys)


def test_r01_r06_loop_ativo_durante_silencio_e_alerta_novo_so_na_retomada(
    monkeypatch, protected_chain, capsys, caplog,
):
    clock, pipeline = protected_chain
    monkeypatch.setattr(connection_manager, "datetime", clock)
    workbook, collector = make_collector(monkeypatch, clock)
    initial = quote(clock)
    workbook.publish(initial)
    bot = object.__new__(bot_module.Bot)
    bot.connection = connection_manager.ConnectionManager()
    bot.collector = collector
    bot.pipeline = pipeline
    bot.logger = Mock()
    published = []
    bot.mostrar = published.append
    cycles = []
    old_alert = None

    def tick(_delay):
        nonlocal old_alert
        assert bot.connection.verificar()["status"] == "ATIVA"
        captured = capsys.readouterr()
        assert "PROFIT_LOOP_ACTIVE" in captured.err
        cycles.append(captured.out)
        count = len(cycles)
        if count == 1:
            old_alert = published[0].alert
            assert old_alert.valid and "BUY" in captured.out
        elif count < 7:
            assert len(published) == 1 and pipeline.context is published[0]
            assert pipeline.context.alert is old_alert and old_alert.valid
            assert "BUY" not in captured.out and "SELL" not in captured.out
        else:
            assert len(published) == 2
            assert published[-1].alert is not old_alert and "BUY" in captured.out
            raise KeyboardInterrupt

        clock.current += timedelta(seconds=35 if count == 4 else 1)
        collector.excel.book = workbook
        if count == 1:
            collector.excel.book = None
        elif count in {2, 4}:
            workbook.publish(initial)
        elif count in {3, 5}:
            workbook.rows = iter((None,))
        else:
            workbook.publish(quote(clock, price=180_040, volume=1100))

    monkeypatch.setattr(bot_module, "time", SimpleNamespace(sleep=tick))
    with caplog.at_level("INFO", logger="market_data.collector"):
        bot.executar()
    assert caplog.messages.count("PROFIT_QUOTE_READ_ATTEMPT") == 7
    assert len(cycles) == 7
    for output, reason in zip(cycles[1:], (
        "READ_ERROR", "DUPLICATE", "READ_ERROR", "STALE_TIMESTAMP", "READ_ERROR", "ACCEPTED",
    )):
        assert reason in output
    assert "GAP_VOLUME_INDETERMINATE" in cycles[-1]
    assert "PROFIT_QUOTE_PUBLISHED" in cycles[-1]
    assert "PROFIT_LOCAL_RECOVERY_COMPLETE" in cycles[-1]


@pytest.mark.parametrize("protected", [False, True], ids=["legado", "protegido"])
@pytest.mark.parametrize("case", ["vazio", "excecao", "incompleto", "divergente", "mistura"])
def test_r02_evidencia_de_leitura(monkeypatch, protected_chain, capsys, protected, case):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock, protected=protected)
    first = quote(clock)
    workbook.publish(first)
    assert collector.get_data() is not None
    capsys.readouterr()
    clock.current += timedelta(seconds=1)
    latest = quote(clock, price=180_060, volume=1400)
    workbook.publish(latest)
    reason = None
    if case in {"vazio", "excecao"}:
        if case == "vazio":
            latest[3] = None
            workbook.publish(latest)
        elif protected:
            workbook.rows = iter((None,))
        else:
            del workbook.cells["D2"]  # range() lança KeyError, suprimido por ler_celula.
        if protected:
            reason = "PROFIT_QUOTE_INVALID_PRICE" if case == "vazio" else "PROFIT_QUOTE_READ_ERROR"
        else:
            reason = "inválido"
    elif case == "incompleto":
        workbook.rows = iter((latest[:-1],))
        if protected:
            reason = "PROFIT_QUOTE_INCOMPLETE_RANGE"
    elif case == "divergente":
        workbook.publish(latest, quote(clock, price=180_080, volume=1400))
        if protected:
            reason = "PROFIT_QUOTE_INCONSISTENT_READ"
    else:
        latest[3] = first[3]
        workbook.publish(latest, latest.copy())

    before = market_state(collector)
    context = collector.get_data()
    if reason:
        assert context is None
        assert reason in capsys.readouterr().out
        assert market_state(collector) == before
    else:
        assert context.market.last_price == latest[3]
        assert sum(candle.volume for candle in context.market.candles) == 400
        assert collector.multi_timeframe.get("M1").last_candle.volume == 400
        assert collector.last_valid_volume == 1400


@pytest.mark.parametrize(
    "interval,interruption,volume,discarded",
    [(29, None, 1400, False), (30, None, 1400, False), (31, None, 1400, True),
     (5, "rejected", 1400, False), (5, "read_error", 1400, True),
     (5, None, 25, False)],
)
def test_r04_intervalos_rejeicao_reset_e_volume(
    monkeypatch, protected_chain, capsys, interval, interruption, volume, discarded,
):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    start = clock.current
    workbook.publish(quote(clock))
    assert collector.get_data() is not None
    if interruption:
        clock.current += timedelta(seconds=1)
        if interruption == "read_error":
            workbook.rows = iter((None,))
            reason = "READ_ERROR"
        else:
            future = row(clock.current + timedelta(seconds=3), price=180_070, volume=1300)
            workbook.publish(future)
            reason = "FUTURE_TIMESTAMP"
        before = market_state(collector)
        assert collector.get_data() is None
        assert market_state(collector) == before
        assert reason in capsys.readouterr().out
    clock.current = start + timedelta(seconds=interval)
    workbook.publish(quote(clock, price=180_040, volume=volume))
    assert collector.get_data() is not None
    out = capsys.readouterr().out
    assert ("GAP_VOLUME_INDETERMINATE" in out) is discarded
    expected = 0 if discarded or volume < 1000 else 400
    for tf in ("M1", "M5", "M15"):
        assert collector.multi_timeframe.get(tf).last_candle.volume == expected
    assert sum(c.volume for c in collector.renko.market.candles) == expected
    assert collector.last_valid_volume == volume
    assert collector._primary_chart_volume == (1000 if discarded else 0 if volume < 1000 else volume)


@pytest.mark.parametrize("protected", [False, True], ids=["legado", "protegido"])
@pytest.mark.parametrize("prefix", ["WIN", "WDO"])
@pytest.mark.parametrize("field", ["simbolo", "VEN"])
def test_r05_troca_e_retorno(monkeypatch, protected_chain, capsys, protected, prefix, field):
    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock, protected=protected)
    symbol = prefix + "Z26"
    workbook.publish(quote(clock, symbol=symbol))
    assert collector.get_data() is not None
    before = market_state(collector)
    flow = deepcopy(collector.order_flow)
    clock.current += timedelta(seconds=1)
    changed = quote(clock, symbol=symbol, price=180_040, volume=1100)
    changed[14:] = [860, 220]
    if field == "simbolo":
        changed[0] = prefix + "G27"
    else:
        changed[10] = "17/02/2027"
    workbook.publish(changed)
    context = collector.get_data()
    if protected:
        assert context is None
        assert "CONTRACT_TRANSITION_BLOCKED" in capsys.readouterr().out
        assert market_state(collector) == before and collector.order_flow == flow
    else:
        assert context.market.symbol == changed[0]
        assert collector.last_closed_renko_bricks == 2
        assert collector.last_valid_volume == 1100
        assert collector.order_flow.sample_count == (0 if field == "simbolo" else 1)

    clock.current += timedelta(seconds=1)
    returned = quote(clock, symbol=symbol, price=180_080, volume=1200)
    returned[14:] = [910, 230]
    workbook.publish(returned)
    recovered = collector.get_data()
    assert recovered.market.symbol == symbol
    assert collector.last_valid_volume == 1200
    assert collector.last_closed_renko_bricks == (4 if protected else 2)
    assert collector.order_flow.cumulative_buy == 910
    assert collector.order_flow.sample_count == (0 if not protected and field == "simbolo"
                                                 else 1 if protected else 2)
    for tf in ("M1", "M5", "M15"):
        candle = collector.multi_timeframe.get(tf).last_candle
        assert (candle.open, candle.close, candle.volume) == (180_000, 180_080, 200)


def test_r06_repeticao_nao_consecutiva_publica_novo_ciclo(
    monkeypatch, protected_chain, capsys,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    a = quote(clock)
    b = quote(clock, price=180_040, volume=1030)
    contexts = []
    fingerprints = []
    for tick in (a, b, a):
        workbook.publish(tick)
        context = collector.get_data()
        contexts.append(context)
        fingerprints.append(collector.source_guard._last_fingerprint)
        assert context.source_timestamp == clock.current.isoformat()
        assert_buy_and_alert(pipeline, context, clock, capsys)
    assert fingerprints[0] == fingerprints[2] != fingerprints[1]
    assert len({id(context) for context in contexts}) == 3
    assert len({id(context.decision) for context in contexts}) == 3
    assert len({id(context.alert) for context in contexts}) == 3
    assert pipeline.context is contexts[-1]
