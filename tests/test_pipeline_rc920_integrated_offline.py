"""Integração offline da publicação e da recuperação da cotação protegida."""

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
from tests.test_pipeline_rc918_integrated_offline import make_collector, market_state
from tests.test_pipeline_rc920_source_recovery_adversarial import quote


def snapshot(collector, pipeline):
    context = pipeline.context
    return (
        market_state(collector), collector._primary_chart_volume,
        deepcopy(collector.order_flow), deepcopy(vars(collector.source_guard)),
        list(pipeline._temporal_primary_history._entries),
        id(context), deepcopy((context.decision, context.alert)),
        collector.last_profit_rtd_receipt, collector.profit_rtd_validation_summary(),
    )


def install_rtd(collector, clock):
    def read(symbol):
        return {
            "symbol": symbol, "timestamp": clock.current.isoformat(),
            "observational_only": True,
            "trades": [{
                "timestamp": clock.current.isoformat(), "buyer": "A", "seller": "B",
                "price": 180_000, "quantity": 1, "aggressor": "Comprador",
            }],
        }

    reader = SimpleNamespace(read_times_trades=Mock(side_effect=read))
    rtd = ProfitRTDOrderFlowPipeline(reader, collector.order_flow)
    collector.enable_profit_rtd_order_flow = True
    collector.profit_rtd_order_flow_pipeline = rtd
    return rtd


def assert_publication(pipeline, context, clock, capsys):
    assert context is not None
    assert context.received_timestamp == clock.current
    output = capsys.readouterr()
    assert "PROFIT_LOOP_ACTIVE" in output.err
    stages = (
        "PROFIT_QUOTE_READ_OK", "PROFIT_QUOTE_ELIGIBLE",
        "PROFIT_QUOTE_ACCEPTED", "PROFIT_QUOTE_PUBLISHED",
    )
    offsets = [output.out.index(stage) for stage in stages]
    assert offsets == sorted(offsets)
    assert_buy_and_alert(pipeline, context, clock, capsys)
    return output.out


def assert_no_publication(capsys, reason):
    output = capsys.readouterr().out
    assert reason in output
    for marker in ("PROFIT_QUOTE_PUBLISHED", "PROFIT_LOCAL_RECOVERY_COMPLETE", "BUY", "SELL"):
        assert marker not in output
    return output


@pytest.mark.parametrize("failure", ["leitura", "apos-dedup"])
def test_a_b_c_d_auxiliar_e_repeticao_da_mesma_cotacao(
    monkeypatch, protected_chain, capsys, caplog, failure,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    workbook.publish(quote(clock))
    original = collector.get_data()
    assert_publication(pipeline, original, clock, capsys)
    assert original.order_flow_state is collector.order_flow
    assert collector.last_profit_rtd_receipt.baseline_reset
    before = snapshot(collector, pipeline)
    previous_trade_signature = rtd.deduplicator._previous

    clock.current += timedelta(seconds=31)
    pending = quote(clock, price=180_060, volume=1450)
    workbook.publish(pending)
    with monkeypatch.context() as fault:
        error = OSError("falha auxiliar sintética")
        if failure == "leitura":
            fault.setattr(rtd.reader.read_times_trades, "side_effect", error)
        else:
            build = Mock(side_effect=error)
            fault.setattr(rtd, "aggression_builder", SimpleNamespace(build=build))
        with caplog.at_level("INFO", logger="market_data.collector"):
            assert collector.get_data() is None
        if failure == "apos-dedup":
            batch = build.call_args.args[0]
            assert batch.baseline_only and batch.timestamp == clock.current.isoformat()
    assert "PROFIT_QUOTE_READ_ATTEMPT" in caplog.messages
    assert_no_publication(capsys, "PROFIT_QUOTE_AUXILIARY_FAILED")
    assert snapshot(collector, pipeline) == before
    assert rtd.deduplicator._previous == previous_trade_signature
    assert collector._primary_gap_pending

    workbook.publish(pending)
    recovered = collector.get_data()
    output = assert_publication(pipeline, recovered, clock, capsys)
    assert output.index("PROFIT_QUOTE_PUBLISHED") < output.index("PROFIT_LOCAL_RECOVERY_COMPLETE")
    assert "reason=PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert recovered is not original and recovered.alert is not original.alert
    assert collector.last_valid_volume == 1450 and collector._primary_chart_volume == 1000
    assert collector.source_guard._last_fingerprint != before[3]["_last_fingerprint"]
    assert collector.last_profit_rtd_receipt.baseline_reset
    assert rtd.deduplicator._previous != previous_trade_signature
    assert collector.order_flow.cumulative_buy == 0 and not collector.order_flow.history
    for tf in ("M1", "M5", "M15"):
        assert collector.multi_timeframe.get(tf).last_candle.volume == 0
    assert collector.last_closed_renko_bricks == 3
    assert sum(c.volume for c in recovered.market.candles) == 0


def test_e_f_g_falha_de_builder_bloqueia_ate_coletor_novo(
    monkeypatch, protected_chain, capsys,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    workbook.publish(quote(clock))
    first = collector.get_data()
    assert_publication(pipeline, first, clock, capsys)
    before = snapshot(collector, pipeline)
    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, price=180_040, volume=1100))
    fault = Mock(side_effect=RuntimeError("falha no builder Renko"))
    monkeypatch.setattr(collector.renko, "update_tick", fault)
    with pytest.raises(RuntimeError, match="falha no builder Renko"):
        collector.get_data()
    assert_no_publication(capsys, "PROFIT_QUOTE_ELIGIBLE")
    partial = snapshot(collector, pipeline)
    assert partial[1:] == before[1:]
    for tf in ("M1", "M5", "M15"):
        candle = collector.multi_timeframe.get(tf).last_candle
        assert (candle.close, candle.volume) == (180_040, 100)
    assert collector.renko.market.last_candle.close == 180_000
    assert collector.last_valid_volume == 1000
    assert collector._last_primary_receipt == first.received_timestamp
    assert collector._primary_publication_blocked
    reads = workbook.block_reads
    rtd_reads = rtd.reader.read_times_trades.call_count

    clock.current += timedelta(seconds=1)
    candidate = quote(clock, price=180_080, volume=1200)
    workbook.publish(candidate)
    assert collector.get_data() is None
    assert_no_publication(capsys, "PROFIT_QUOTE_REINITIALIZATION_REQUIRED")
    assert snapshot(collector, pipeline) == partial
    assert workbook.block_reads == reads and rtd.reader.read_times_trades.call_count == rtd_reads
    fault.assert_called_once()

    new_workbook, replacement = make_collector(monkeypatch, clock)
    install_rtd(replacement, clock)
    new_workbook.publish(candidate)
    recovered = replacement.get_data()
    output = assert_publication(pipeline, recovered, clock, capsys)
    assert "PROFIT_LOCAL_RECOVERY_COMPLETE" not in output
    assert recovered is not first and recovered.alert is not first.alert
    assert replacement.last_profit_rtd_receipt.baseline_reset
    for market in [replacement.multi_timeframe.get(tf) for tf in ("M1", "M5", "M15")] + [
        replacement.renko.market,
    ]:
        assert market.candle_count == 1
        assert (market.last_candle.open, market.last_candle.volume) == (180_080, 0)


@pytest.mark.parametrize("seconds", [29, 30, 31, 65])
def test_h_i_volume_no_limite_de_continuidade(monkeypatch, protected_chain, capsys, seconds):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    install_rtd(collector, clock)
    workbook.publish(quote(clock))
    assert_publication(pipeline, collector.get_data(), clock, capsys)
    clock.current += timedelta(seconds=seconds)
    workbook.publish(quote(clock, price=180_060, volume=1500))
    context = collector.get_data()
    output = assert_publication(pipeline, context, clock, capsys)
    rebase = seconds > 30
    assert ("PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE" in output) is rebase
    assert ("reason=PROFIT_QUOTE_INTERVAL_EXCEEDED" in output) is rebase
    # The synthetic RTD window contains just one trade and changes on each read.
    # It loses overlap even when the primary quote has no continuity gap.
    receipt = collector.last_profit_rtd_receipt
    assert receipt.baseline_reset
    assert receipt.continuity == ("BASELINE_ESTABLISHED" if rebase else "OVERLAP_LOST_REBASE")
    expected = 0 if rebase else 500
    for tf in ("M1", "M5", "M15"):
        market = collector.multi_timeframe.get(tf)
        assert market.last_candle.volume == expected
    assert sum(c.volume for c in context.market.candles) == expected
    assert collector.last_closed_renko_bricks == 3


@pytest.mark.parametrize(
    "case,reason",
    [("bloco", "PROFIT_QUOTE_INCOMPLETE_RANGE"),
     ("WIN", "TEMPORAL_CONTRACT_TRANSITION_BLOCKED"),
     ("WDO", "TEMPORAL_CONTRACT_TRANSITION_BLOCKED")],
)
def test_k_l_bloco_incompleto_e_rollover(monkeypatch, protected_chain, capsys, case, reason):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    symbol = "WDOZ26" if case == "WDO" else "WINZ26"
    workbook.publish(quote(clock, symbol=symbol))
    assert_publication(pipeline, collector.get_data(), clock, capsys)
    before = snapshot(collector, pipeline)
    clock.current += timedelta(seconds=1)
    if case == "bloco":
        workbook.rows = iter((quote(clock, symbol=symbol)[:-1],))
    else:
        workbook.publish(quote(clock, symbol=case + "G27", expiry="17/02/2027"))
    assert collector.get_data() is None
    assert_no_publication(capsys, reason)
    assert snapshot(collector, pipeline) == before
    assert collector._primary_gap_pending is (case == "bloco")
    rtd.reader.read_times_trades.assert_called_once()


def test_j_n_loop_ativo_excel_indisponivel_e_silencio(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    original = quote(clock)
    workbook.publish(original)
    first = collector.get_data()
    assert_publication(pipeline, first, clock, capsys)
    before = snapshot(collector, pipeline)
    monkeypatch.setattr(connection_manager, "datetime", clock)
    bot = object.__new__(bot_module.Bot)
    bot.connection = connection_manager.ConnectionManager()
    bot.collector, bot.pipeline, bot.logger = collector, pipeline, Mock()
    bot.mostrar = Mock()
    statuses = []

    def next_cycle(_seconds):
        statuses.append(bot.connection.verificar()["status"])
        if len(statuses) == 2:
            raise KeyboardInterrupt
        collector.excel.book = workbook
        clock.current += timedelta(seconds=40)
        workbook.publish(original)

    collector.excel.book = None
    monkeypatch.setattr(bot_module, "time", SimpleNamespace(sleep=next_cycle))
    bot.executar()
    assert statuses == ["ATIVA", "ATIVA"]
    bot.mostrar.assert_not_called()
    assert snapshot(collector, pipeline) == before
    output = capsys.readouterr()
    assert output.err.count("PROFIT_LOOP_ACTIVE") == 2
    assert "PROFIT_QUOTE_READ_ERROR" in output.out
    assert "TEMPORAL_STALE_TIMESTAMP" in output.out
    assert "PROFIT_QUOTE_PUBLISHED" not in output.out and "BUY" not in output.out
    assert pipeline.context is first and first.alert.valid


def test_m_repeticao_nao_consecutiva_publica_ciclos_distintos(
    monkeypatch, protected_chain, capsys,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    install_rtd(collector, clock)
    a = quote(clock)
    b = quote(clock, price=180_020, volume=1030)
    contexts, signatures = [], []
    for tick in (a, b, a):
        workbook.publish(tick)
        context = collector.get_data()
        assert_publication(pipeline, context, clock, capsys)
        contexts.append(context)
        signatures.append(collector.source_guard._last_fingerprint)
    assert signatures[0] == signatures[2] != signatures[1]
    assert len({id(c) for c in contexts}) == len({id(c.alert) for c in contexts}) == 3
    assert all(c.source_timestamp == clock.current.isoformat() for c in contexts)


def test_o_legado_preserva_leitura_e_atribuicao_de_volume(monkeypatch, offline_chain, capsys):
    clock, pipeline = offline_chain
    workbook, collector = make_collector(monkeypatch, clock, protected=False)
    assert collector.temporal_primary_policy is pipeline.temporal_primary_policy is None
    workbook.publish(quote(clock))
    assert_buy_and_alert(pipeline, collector.get_data(), clock, capsys)
    clock.current += timedelta(seconds=65)
    workbook.publish(quote(clock, price=180_060, volume=1500))
    context = collector.get_data()
    output = capsys.readouterr()
    assert "PROFIT_LOOP_ACTIVE" not in output.err
    assert "PROFIT_QUOTE_PUBLISHED" not in output.out
    assert workbook.block_reads == 0
    assert sum(c.volume for c in context.market.candles) == 500
    assert_buy_and_alert(pipeline, context, clock, capsys)
