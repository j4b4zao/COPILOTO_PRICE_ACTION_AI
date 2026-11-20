"""Regressão offline do contrato protegido introduzido na RC9.21-A3."""

from builtins import print as console_print
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import DEFAULT, Mock

import pytest

from app import bot as bot_module
from core.connection_manager import ConnectionManager
from market_data import collector as collector_module
from tests.test_pipeline_rc917_freshness_adversarial import offline_chain, protected_chain
from tests.test_pipeline_rc918_integrated_offline import make_collector
from tests.test_pipeline_rc920_integrated_offline import assert_publication, install_rtd
from tests.test_pipeline_rc920_source_recovery_adversarial import quote
from tests.test_pipeline_rc921_transactional_adversarial import (
    TIMEFRAMES,
    InjectedFailure,
    assert_shared,
    context_image,
    fail_at,
    inject_collector_fault,
    state_image,
    transaction,
)


@pytest.mark.parametrize("point,new_snapshot", [
    ("A-antes-M1", False),
    ("B-dentro-M1", False),
    ("C-entre-M1-M5", False),
    ("D-entre-M5-M15", False),
    ("E-antes-Renko", True),
    ("F-dentro-Renko", False),
    ("G-publicacao-RTD", False),
    ("H-diagnosticos", True),
    ("I-marcadores", False),
])
def test_preparation_failure_keeps_last_publication_and_allows_retry(
    transaction, monkeypatch, capsys, point, new_snapshot,
):
    clock, pipeline, workbook, collector, _, previous = transaction
    rtd = collector.profit_rtd_order_flow_pipeline
    before = state_image(collector, rtd)
    retained = context_image(previous)
    published_dict = vars(collector)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    injected = InjectedFailure(point)

    fork = collector._fork_protected_cycle
    with monkeypatch.context() as patch:
        def fork_with_fault():
            prepared = fork()
            inject_collector_fault(patch, prepared, point, injected)
            return prepared

        patch.setattr(collector, "_fork_protected_cycle", fork_with_fault)
        with pytest.raises(InjectedFailure) as raised:
            collector.get_data()
        assert raised.value is injected
        assert vars(collector) is published_dict
    assert "PROFIT_QUOTE_ACCEPTED" not in capsys.readouterr().out
    assert state_image(collector, rtd) == before
    assert collector.profit_rtd_order_flow_pipeline is rtd
    assert pipeline.context is previous
    assert_shared(previous, collector)
    assert context_image(previous) == retained

    if new_snapshot:
        clock.current += timedelta(seconds=1)
        pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    current = collector.get_data()
    output = assert_publication(pipeline, current, clock, capsys)
    assert output.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert context_image(previous) == retained
    assert current is not previous
    assert current.market is not previous.market
    assert current.multi_timeframe is not previous.multi_timeframe
    assert current.order_flow_state is not previous.order_flow_state
    assert_shared(current, collector)
    assert collector.profit_rtd_order_flow_pipeline.state_adapter.state is current.order_flow_state
    assert collector.last_profit_rtd_receipt.new_trade_count == 1
    assert current.order_flow_state.cumulative_buy == 1
    assert collector.last_closed_renko_bricks == 3
    assert sum(candle.volume for candle in current.market.candles) == 100
    for tf in TIMEFRAMES:
        market = current.multi_timeframe.get(tf)
        old_market = previous.multi_timeframe.get(tf)
        assert market.candle_count == old_market.candle_count == 1
        assert market.last_candle is not old_market.last_candle
        assert (market.last_candle.close, market.last_candle.volume) == (180_060, 100)

    workbook.publish(pending)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_DUPLICATE" in capsys.readouterr().out


def test_acceptance_diagnostic_failure_does_not_consume_delivery(transaction, monkeypatch, capsys):
    clock, pipeline, workbook, collector, _, previous = transaction
    retained = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    attempts = []

    def fail_acceptance_log(*args, **kwargs):
        if args == ("[DATA ACCEPTED] PROFIT_QUOTE_ACCEPTED",):
            attempts.append(collector._last_primary_receipt)
            raise OSError("saída indisponível")
        console_print(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(collector_module, "print", fail_acceptance_log, raising=False)
        context = collector.get_data()
    assert attempts == [clock.current]
    assert "PROFIT_QUOTE_PUBLISHED" in capsys.readouterr().out
    assert context is not None and context.received_timestamp == clock.current
    assert context_image(previous) == retained
    assert pipeline.executar(context) is context
    assert context.alert.valid
    workbook.publish(pending)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_DUPLICATE" in capsys.readouterr().out


@pytest.mark.parametrize("phase", ["analise", "apresentacao"])
def test_consumer_failure_does_not_redeliver_or_mutate_previous_context(
    transaction, monkeypatch, capsys, phase,
):
    clock, pipeline, workbook, collector, _, previous = transaction
    retained = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    bot = object.__new__(bot_module.Bot)
    bot.connection, bot.collector, bot.pipeline = ConnectionManager(), collector, pipeline
    bot.logger = Mock()
    present = Mock(wraps=bot.mostrar)
    bot.mostrar = present

    with monkeypatch.context() as patch:
        error = InjectedFailure(phase)
        if phase == "analise":
            score = next(engine for engine in pipeline.engines if type(engine).__name__ == "ScoreEngine")
            fail_at(patch, score, "executar", error, after=True)
        else:
            fail_at(patch, bot_module.OrderFlowMonitor, "render", error)
        patch.setattr(bot_module, "time", SimpleNamespace(sleep=Mock()))
        stop_on_second_cycle = Mock(
            wraps=bot.connection.atualizar, side_effect=[DEFAULT, KeyboardInterrupt()],
        )
        patch.setattr(bot.connection, "atualizar", stop_on_second_cycle)
        bot.executar()

    bot.logger.erro.assert_called_once_with(phase)
    delivered = pipeline.context
    assert delivered is not previous and delivered.received_timestamp == clock.current
    assert delivered.alert.valid is (phase == "apresentacao")
    assert delivered.decision.valid is (phase == "apresentacao")
    assert present.call_count == (1 if phase == "apresentacao" else 0)
    assert capsys.readouterr().out.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert context_image(previous) == retained
    workbook.publish(pending)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_DUPLICATE" in capsys.readouterr().out
    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, price=180_080, volume=1200))
    assert_publication(pipeline, collector.get_data(), clock, capsys)
    assert context_image(previous) == retained


def test_isolation_failure_requires_reinitialization(transaction, monkeypatch, capsys):
    clock, pipeline, workbook, collector, _, previous = transaction
    rtd = collector.profit_rtd_order_flow_pipeline
    before = state_image(collector, rtd)
    retained = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    reads = workbook.block_reads
    with monkeypatch.context() as patch:
        fail_at(patch, collector, "_fork_protected_cycle", TypeError("estado não copiável"))
        with pytest.raises(RuntimeError, match="PROFIT_QUOTE_REINITIALIZATION_REQUIRED") as raised:
            collector.get_data()
    assert isinstance(raised.value.__cause__, TypeError)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_REINITIALIZATION_REQUIRED" in capsys.readouterr().out
    assert workbook.block_reads == reads
    assert state_image(collector, rtd) == {**before, "blocked": True}
    assert context_image(previous) == retained

    new_workbook, replacement = make_collector(monkeypatch, clock)
    install_rtd(replacement, clock)
    new_workbook.publish(pending)
    current = replacement.get_data()
    assert_publication(pipeline, current, clock, capsys)
    assert replacement.last_profit_rtd_receipt.baseline_reset
    assert current.market.last_candle.volume == 0
    assert context_image(previous) == retained


@pytest.mark.parametrize("seconds,attributed", [(29, 100), (30, 100), (31, 0)])
def test_continuity_attributes_volume_only_to_current_context(
    transaction, capsys, seconds, attributed,
):
    clock, pipeline, workbook, collector, _, previous = transaction
    retained = context_image(previous)
    clock.current += timedelta(seconds=seconds)
    workbook.publish(quote(clock, price=180_060, volume=1100))
    context = collector.get_data()
    output = assert_publication(pipeline, context, clock, capsys)
    assert ("reason=PROFIT_QUOTE_INTERVAL_EXCEEDED" in output) is (seconds == 31)
    assert collector._primary_chart_volume == 1000 + attributed
    assert collector.last_valid_volume == 1100
    assert sum(candle.volume for candle in context.market.candles) == attributed
    for tf in TIMEFRAMES:
        assert context.multi_timeframe.get(tf).last_candle.volume == attributed
    assert context_image(previous) == retained


@pytest.mark.parametrize("phase", ["leitura", "apos-dedup"])
def test_auxiliary_failure_keeps_committed_flow_and_allows_same_quote(
    transaction, monkeypatch, capsys, phase,
):
    clock, pipeline, workbook, collector, _, previous = transaction
    rtd = collector.profit_rtd_order_flow_pipeline
    before = state_image(collector, rtd)
    retained = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    error = InjectedFailure(phase)
    with monkeypatch.context() as patch:
        if phase == "leitura":
            patch.setattr(rtd.reader.read_times_trades, "side_effect", error)
        else:
            builder = SimpleNamespace(build=Mock(side_effect=error))
            patch.setattr(rtd, "aggression_builder", builder)
        assert collector.get_data() is None
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert state_image(collector, rtd) == {
        **before, "recovery": (True, "PROFIT_QUOTE_AUXILIARY_FAILED"),
    }
    assert context_image(previous) == retained
    workbook.publish(pending)
    context = collector.get_data()
    output = assert_publication(pipeline, context, clock, capsys)
    assert "reason=PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert collector.last_profit_rtd_receipt.baseline_reset
    assert collector.profit_rtd_order_flow_pipeline.deduplicator._previous != before["rtd"][0]["_previous"]
    assert collector._primary_chart_volume == 1000
    assert context_image(previous) == retained
