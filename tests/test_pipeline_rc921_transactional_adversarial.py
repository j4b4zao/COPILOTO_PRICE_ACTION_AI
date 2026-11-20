"""Valida as fronteiras transacionais RC9.21 com Excel e negocios sinteticos."""

from builtins import print as console_print
from copy import deepcopy
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


TIMEFRAMES = ("M1", "M5", "M15")
CHARTS = {"builder:M1", "builder:M5", "builder:M15", *TIMEFRAMES, "Renko"}
MULTI_TIMEFRAME_DONE = {"new_candles"}
RENKO_DONE = {"renko_count"}
ACCEPTANCE = {"primary_signature", "temporal_history", "receipt_time", "volume"}
DERIVED = {"flow", "rtd", "diagnostics", "quality", "session"}
COMPLETE = CHARTS | MULTI_TIMEFRAME_DONE | RENKO_DONE | ACCEPTANCE | DERIVED


class InjectedFailure(RuntimeError):
    pass


def market_image(market):
    return (
        market.symbol, market.timeframe, market.timestamp, market.last_price,
        market.volume, market.candles.all(),
    )


def context_image(context):
    return deepcopy((
        market_image(context.market),
        {tf: market_image(context.multi_timeframe.get(tf)) for tf in TIMEFRAMES},
        context.order_flow_state, context.source_timestamp, context.received_timestamp,
        context.decision, context.alert,
    ))


def state_image(collector, rtd):
    image = {
        tf: market_image(collector.multi_timeframe.get(tf)) for tf in TIMEFRAMES
    }
    image.update({
        f"builder:{tf}": vars(builder)
        for tf, builder in collector.multi_timeframe._builders.items()
    })
    renko = collector.renko
    image.update(
        Renko=(market_image(renko.market), renko._current_open,
               renko._last_cumulative_volume, renko._brick_start_volume),
        new_candles=collector.last_new_candles,
        renko_count=collector.last_closed_renko_bricks,
        flow=collector.order_flow,
        rtd=(vars(rtd.deduplicator),
             (rtd.state_adapter._symbol, rtd.state_adapter._cumulative_buy,
              rtd.state_adapter._cumulative_sell),
             collector.last_profit_rtd_receipt, collector.profit_rtd_validation_summary()),
        diagnostics=vars(collector.source_diagnostics),
        quality=collector.last_delta_quality,
        session=collector.delta_session_recorder.samples,
        primary_signature=vars(collector.source_guard),
        temporal_history=collector._temporal_primary_history._entries,
        contract=collector._primary_contract,
        receipt_time=collector._last_primary_receipt,
        volume=(collector.last_valid_volume, collector._primary_chart_volume),
        recovery=(collector._primary_gap_pending, collector._primary_gap_reason),
        blocked=collector._primary_publication_blocked,
    )
    return deepcopy(image)


def assert_shared(previous, collector):
    assert previous.market is collector.market is collector.renko.market
    assert previous.multi_timeframe is collector.multi_timeframe
    assert previous.order_flow_state is collector.order_flow
    for tf in TIMEFRAMES:
        builder = collector.multi_timeframe._builders[tf]
        assert builder.current is previous.multi_timeframe.get(tf).last_candle


@pytest.fixture
def transaction(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    read = rtd.reader.read_times_trades.side_effect
    baseline = read("WINZ26")["trades"][0]

    def overlapping_window(symbol):
        payload = read(symbol)
        if payload["trades"][0] != baseline:
            payload["trades"].append(baseline)
        return payload

    rtd.reader.read_times_trades.side_effect = overlapping_window
    workbook.publish(quote(clock))
    previous = collector.get_data()
    assert_publication(pipeline, previous, clock, capsys)
    return clock, pipeline, workbook, collector, rtd, previous


def fail_at(patch, target, name, error, *, after=False):
    original = getattr(target, name)

    def injected(*args, **kwargs):
        if after:
            original(*args, **kwargs)
        raise error

    patch.setattr(target, name, injected)


def inject_collector_fault(patch, collector, point, error):
    builders = collector.multi_timeframe._builders
    if point == "A-antes-M1":
        fail_at(patch, builders["M1"], "update", error)
    elif point == "B-dentro-M1":
        fail_at(patch, builders["M1"], "_calculate_period_volume", error, after=True)
    elif point == "C-entre-M1-M5":
        fail_at(patch, builders["M5"], "update", error)
    elif point == "D-entre-M5-M15":
        fail_at(patch, builders["M15"], "update", error)
    elif point == "E-antes-Renko":
        fail_at(patch, collector.renko, "update_tick", error)
    elif point == "F-dentro-Renko":
        fail_at(patch, collector.renko, "_add_current", error, after=True)
    elif point == "G-publicacao-RTD":
        fail_at(patch, collector.profit_rtd_order_flow_pipeline, "publish", error, after=True)
    elif point == "H-diagnosticos":
        fail_at(patch, collector.delta_quality_validator, "evaluate", error)
    elif point == "I-marcadores":
        fail_at(patch, collector._temporal_primary_history, "record", error)
    elif point == "J-aceite-sem-retorno":
        def fail_after_acceptance(*args, **kwargs):
            console_print(*args, **kwargs)
            if args == ("[DATA ACCEPTED] PROFIT_QUOTE_ACCEPTED",):
                raise error

        patch.setattr(collector_module, "print", fail_after_acceptance, raising=False)
    else:
        raise AssertionError(f"Ponto de injeção desconhecido: {point}")


def record_transition(record_property, point, error, before, after, context_before,
                      context_after, *, partial, retry, severity, duplication, loss,
                      publication):
    evidence = {
        "classificacao": "REPRODUZIDO",
        "injecao": point,
        "excecao": repr(error) if error is not None else "nenhuma",
        "estado_anterior": repr(before),
        "estado_posterior": repr(after),
        "estados_alterados": sorted(key for key in before if before[key] != after[key]),
        "contexto_anterior": repr(context_before),
        "contexto_posterior": repr(context_after),
        "contexto_alterado": context_before != context_after,
        "mutacao_parcial": partial,
        "bloqueado": after["blocked"],
        "publicacao": publication,
        "retry": retry,
        "risco_duplicacao_inferido": duplication,
        "risco_perda_inferido": loss,
        "severidade": severity,
    }
    for name, value in evidence.items():
        record_property(name, value)


def assert_duplicate(workbook, collector, rtd, quote_row, capsys):
    before = state_image(collector, rtd)
    quote_reads = workbook.block_reads
    rtd_reads = rtd.reader.read_times_trades.call_count
    workbook.publish(quote_row)
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_DUPLICATE" in output
    assert "PROFIT_QUOTE_ACCEPTED" not in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert state_image(collector, rtd) == before
    assert workbook.block_reads == quote_reads + 2
    assert rtd.reader.read_times_trades.call_count == rtd_reads


def assert_detached(previous, current, collector, retained):
    assert context_image(previous) == retained
    assert current is not previous
    assert_shared(current, collector)
    assert current.market is not previous.market
    assert current.multi_timeframe is not previous.multi_timeframe
    assert current.order_flow_state is not previous.order_flow_state
    for tf in TIMEFRAMES:
        earlier = previous.multi_timeframe.get(tf)
        latest = current.multi_timeframe.get(tf)
        assert latest is not earlier
        assert latest.last_candle is not earlier.last_candle


def assert_attributed_volume(context, volume):
    assert sum(candle.volume for candle in context.market.candles) == volume
    for tf in TIMEFRAMES:
        assert context.multi_timeframe.get(tf).last_candle.volume == volume


def check_acceptance_failures(transaction, capsys):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    retained = context_image(previous)
    report = collector._report_protected_acceptance
    events = []
    diagnostic_error = InjectedFailure("diagnostico de aceite")
    delivery_error = InjectedFailure("interrupcao antes do retorno")
    clock.current += timedelta(seconds=1)
    first_quote = quote(clock, price=180_060, volume=1100)
    workbook.publish(first_quote)

    def fail_diagnostic(*args, **kwargs):
        if args == ("[DATA ACCEPTED] PROFIT_QUOTE_ACCEPTED",):
            events.append((collector._last_primary_receipt, pipeline.context))
            raise diagnostic_error
        console_print(*args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(collector_module, "print", fail_diagnostic, raising=False)
        current = collector.get_data()
    assert len(events) == 1
    assert events[0][0] == clock.current and events[0][1] is previous
    assert current is not None
    output = capsys.readouterr().out
    assert output.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert pipeline.context is previous
    assert_detached(previous, current, collector, retained)
    assert_attributed_volume(current, 100)
    assert rtd.state_adapter.state is current.order_flow_state
    assert pipeline.executar(current) is current
    capsys.readouterr()
    assert_duplicate(workbook, collector, rtd, first_quote, capsys)

    current_image = context_image(current)
    before = state_image(collector, rtd)
    clock.current += timedelta(seconds=1)
    second_quote = quote(clock, price=180_080, volume=1200)
    workbook.publish(second_quote)
    delivered = []
    accepted = []

    def interrupt_after_accept(live, reason):
        assert live is collector
        assert pipeline.context is current
        assert context_image(current) == current_image
        assert not delivered
        assert live._last_primary_receipt == clock.current
        accepted.append(state_image(live, rtd))
        report(reason)
        raise delivery_error

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(type(collector), "_report_protected_acceptance", interrupt_after_accept)
        with pytest.raises(InjectedFailure) as raised:
            delivered.append(collector.get_data())
    assert raised.value is delivery_error
    assert not delivered and len(accepted) == 1
    assert state_image(collector, rtd) == accepted[0]
    assert {key for key in before if before[key] != accepted[0][key]} <= COMPLETE
    assert collector.last_valid_volume == collector._primary_chart_volume == 1200
    assert collector.last_closed_renko_bricks == 1
    assert collector.renko.market.candle_count == 5
    assert [c.volume for c in collector.renko.market.candles] == [100, 0, 0, 100, 0]
    assert rtd.state_adapter.state is collector.order_flow
    assert collector.last_profit_rtd_receipt.continuity == "OVERLAP_LOST_REBASE"
    assert collector.last_profit_rtd_receipt.baseline_reset
    assert collector.last_profit_rtd_receipt.new_trade_count == 0
    assert collector.order_flow.cumulative_buy == 0
    for tf in TIMEFRAMES:
        market = collector.multi_timeframe.get(tf)
        assert market is not current.multi_timeframe.get(tf)
        assert (market.last_candle.close, market.last_candle.volume) == (180_080, 200)
    output = capsys.readouterr().out
    assert output.count("PROFIT_QUOTE_ACCEPTED") == 1
    assert output.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert_duplicate(workbook, collector, rtd, second_quote, capsys)
    assert context_image(current) == current_image
    assert context_image(previous) == retained
    return delivery_error


@pytest.mark.parametrize("point", [
    "A-antes-M1", "B-dentro-M1", "C-entre-M1-M5", "D-entre-M5-M15",
    "E-antes-Renko", "F-dentro-Renko", "G-publicacao-RTD", "H-diagnosticos",
    "I-marcadores", "J-aceite-sem-retorno",
])
def test_collector_failure_boundaries(transaction, monkeypatch, capsys, record_property, point):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    retained = context_image(previous)
    if point == "J-aceite-sem-retorno":
        error = check_acceptance_failures(transaction, capsys)
        record_transition(
            record_property, point, error, before, state_image(collector, rtd),
            retained, context_image(previous), partial=False, retry="repeticao deduplicada",
            severity="alta", duplication="nenhuma", loss="interrupcao apos aceite",
            publication="diagnostico absorvido e interrupcao antes do retorno verificados",
        )
        return

    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    injected = InjectedFailure(point)
    fork = type(collector)._fork_protected_cycle
    collect = type(collector)._collect_cycle
    observed = []

    def observe_failure(candidate):
        try:
            return collect(candidate)
        except InjectedFailure as error:
            assert error is injected
            assert state_image(collector, rtd) == before
            assert context_image(previous) == retained
            observed.append(state_image(candidate, candidate.profit_rtd_order_flow_pipeline))
            raise

    with monkeypatch.context() as fault:
        def prepare(live):
            candidate = fork(live)
            assert candidate is not live
            assert candidate.order_flow is not live.order_flow
            assert candidate.profit_rtd_order_flow_pipeline is not rtd
            inject_collector_fault(fault, candidate, point, injected)
            return candidate

        fault.setattr(type(collector), "_fork_protected_cycle", prepare)
        fault.setattr(type(collector), "_collect_cycle", observe_failure)
        with pytest.raises(InjectedFailure) as raised:
            collector.get_data()
    assert raised.value is injected and len(observed) == 1
    candidate_state = observed[0]
    if point in {"F-dentro-Renko", "G-publicacao-RTD", "H-diagnosticos", "I-marcadores"}:
        assert candidate_state["Renko"] != before["Renko"]
    if point == "G-publicacao-RTD":
        assert candidate_state["flow"].cumulative_buy == 1
        assert candidate_state["rtd"][0] != before["rtd"][0]
    if point == "H-diagnosticos":
        assert candidate_state["quality"] == before["quality"]
    if point == "I-marcadores":
        assert candidate_state["quality"] != before["quality"]
        assert candidate_state["temporal_history"] == before["temporal_history"]

    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_ELIGIBLE" in output
    assert "PROFIT_QUOTE_ACCEPTED" not in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert state_image(collector, rtd) == before
    assert pipeline.context is previous
    assert_shared(previous, collector)

    workbook.publish(pending)
    current = collector.get_data()
    assert assert_publication(pipeline, current, clock, capsys).count("PROFIT_QUOTE_PUBLISHED") == 1
    assert collector.last_valid_volume == collector._primary_chart_volume == 1100
    assert collector.last_closed_renko_bricks == 3
    assert collector.last_new_candles == dict.fromkeys(TIMEFRAMES, False)
    assert collector.last_profit_rtd_receipt.new_trade_count == 1
    assert current.order_flow_state.cumulative_buy == 1
    assert_attributed_volume(current, 100)
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert_detached(previous, current, collector, retained)
    record_transition(
        record_property, point, injected, before, state_image(collector, rtd),
        retained, context_image(previous), partial=False, retry="mesma cotacao aceita",
        severity="alta", duplication="nenhuma", loss="nenhuma apos retry",
        publication="candidata descartada; retry publicado uma vez",
    )


@pytest.mark.parametrize("point", ["K-analise", "L-apresentacao"])
def test_failure_after_collector_delivery(transaction, monkeypatch, capsys, record_property, point):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    old_context = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    bot = object.__new__(bot_module.Bot)
    bot.connection, bot.collector, bot.pipeline = ConnectionManager(), collector, pipeline
    bot.logger = Mock()
    injected = InjectedFailure(point)
    presentation_reached = []

    with monkeypatch.context() as fault:
        if point == "K-analise":
            score = next(engine for engine in pipeline.engines if type(engine).__name__ == "ScoreEngine")
            fail_at(fault, score, "executar", injected, after=True)
        else:
            def fail_render(context):
                presentation_reached.append(context)
                raise injected

            fault.setattr(bot_module.OrderFlowMonitor, "render", staticmethod(fail_render))
        fault.setattr(bot_module, "time", SimpleNamespace(sleep=Mock()))
        stop_on_second_cycle = Mock(
            wraps=bot.connection.atualizar, side_effect=[DEFAULT, KeyboardInterrupt()],
        )
        fault.setattr(bot.connection, "atualizar", stop_on_second_cycle)
        bot.executar()

    bot.logger.erro.assert_called_once_with(point)
    assert "PROFIT_QUOTE_PUBLISHED" in capsys.readouterr().out
    delivered = pipeline.context
    assert delivered is not previous
    assert delivered.received_timestamp == clock.current
    assert delivered.alert.valid is (point == "L-apresentacao")
    assert delivered.decision.valid is (point == "L-apresentacao")
    assert presentation_reached == ([delivered] if point == "L-apresentacao" else [])
    after = state_image(collector, rtd)
    assert {key for key in before if before[key] != after[key]} == COMPLETE
    assert not after["blocked"]
    assert_detached(previous, delivered, collector, old_context)
    delivered_image = context_image(delivered)
    assert_attributed_volume(delivered, 100)
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert context_image(delivered) == delivered_image
    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, price=180_080, volume=1200))
    current = collector.get_data()
    assert_publication(pipeline, current, clock, capsys)
    assert_detached(delivered, current, collector, delivered_image)
    assert context_image(previous) == old_context
    record_transition(
        record_property, point, injected, before, after, old_context, context_image(previous),
        partial=False, retry="mesma deduplicada; nova aceita", severity="alta",
        duplication="nenhuma", loss="processamento do consumidor interrompido",
        publication="contexto entregue; consumidor interrompido",
    )


def test_new_collector_restarts_after_partial_candle_update(
    transaction, monkeypatch, capsys, record_property,
):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    old_context = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    with monkeypatch.context() as fault:
        fail_at(fault, collector.multi_timeframe._builders["M5"], "update",
                InjectedFailure("entre M1 e M5"))
        with pytest.raises(InjectedFailure, match="entre M1 e M5") as raised:
            collector.get_data()
    assert isinstance(raised.value, InjectedFailure)
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_ELIGIBLE" in output
    assert "PROFIT_QUOTE_ACCEPTED" not in output and "PROFIT_QUOTE_PUBLISHED" not in output
    assert state_image(collector, rtd) == before
    assert pipeline.context is previous
    assert_shared(previous, collector)

    workbook.publish(pending)
    recovered = collector.get_data()
    assert assert_publication(pipeline, recovered, clock, capsys).count("PROFIT_QUOTE_PUBLISHED") == 1
    assert_attributed_volume(recovered, 100)
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert_detached(previous, recovered, collector, old_context)

    accepted = state_image(collector, rtd)
    retained = context_image(recovered)
    clock.current += timedelta(seconds=1)
    newer = quote(clock, price=180_080, volume=1200)
    workbook.publish(newer)
    reads = workbook.block_reads, rtd.reader.read_times_trades.call_count
    copy_error = TypeError("estado sem copia isolada")

    def refuse_copy(renko, memo):
        assert renko is collector.renko
        raise copy_error

    reason = "PROFIT_QUOTE_REINITIALIZATION_REQUIRED"
    with monkeypatch.context() as fault:
        fault.setattr(type(collector.renko), "__deepcopy__", refuse_copy, raising=False)
        with pytest.raises(RuntimeError, match=reason) as blocked:
            collector.get_data()
    assert blocked.value.__cause__ is copy_error
    assert "PROFIT_QUOTE_PUBLISHED" not in capsys.readouterr().out
    for row in (newer, quote(clock, price=180_100, volume=1300)):
        workbook.publish(row)
        assert collector.get_data() is None
        output = capsys.readouterr().out
        assert reason in output and "PROFIT_QUOTE_PUBLISHED" not in output
    assert (workbook.block_reads, rtd.reader.read_times_trades.call_count) == reads
    assert state_image(collector, rtd) == {**accepted, "blocked": True}
    assert pipeline.context is recovered

    new_workbook, replacement = make_collector(monkeypatch, clock)
    new_rtd = install_rtd(replacement, clock)
    new_workbook.publish(newer)
    current = replacement.get_data()
    assert_publication(pipeline, current, clock, capsys)
    assert new_rtd is not rtd
    assert replacement.last_profit_rtd_receipt.baseline_reset
    assert replacement.last_valid_volume == replacement._primary_chart_volume == 1200
    assert replacement.last_closed_renko_bricks == 0
    for market in [current.market, *(current.multi_timeframe.get(tf) for tf in TIMEFRAMES)]:
        assert market.candle_count == 1
        assert (market.last_candle.open, market.last_candle.close, market.last_candle.volume) == (
            180_080, 180_080, 0,
        )
    assert state_image(collector, rtd) == {**accepted, "blocked": True}
    assert_detached(recovered, current, replacement, retained)
    assert context_image(previous) == old_context
    record_transition(
        record_property, "falha em M5 e falha na copia", copy_error, accepted,
        state_image(collector, rtd), retained, context_image(recovered), partial=False,
        retry="mesmo coletor apos M5; novo coletor apos falha de copia",
        severity="alta", duplication="nenhuma", loss="nenhuma mutacao do publicado",
        publication="retomada com bases novas",
    )


@pytest.mark.parametrize(
    "original,changed,expiry",
    [("WINZ26", "WDOZ26", "16/12/2026"), ("WDOZ26", "WINZ26", "16/12/2026"),
     ("WINZ26", "WING27", "17/02/2027")],
    ids=["WIN-WDO", "WDO-WIN", "rollover"],
)
def test_contract_transitions_leave_accepted_state_intact(
    monkeypatch, protected_chain, capsys, record_property, original, changed, expiry,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    workbook.publish(quote(clock, symbol=original))
    previous = collector.get_data()
    assert_publication(pipeline, previous, clock, capsys)
    before = state_image(collector, rtd)
    old_context = context_image(previous)
    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, symbol=changed, expiry=expiry, price=180_040))
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert "TEMPORAL_CONTRACT_TRANSITION_BLOCKED" in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    after = state_image(collector, rtd)
    assert after == before
    assert context_image(previous) == old_context
    rtd.reader.read_times_trades.assert_called_once()
    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, symbol=original, price=180_060, volume=1100))
    assert_publication(pipeline, collector.get_data(), clock, capsys)
    record_transition(
        record_property, f"guarda de contrato {original} → {changed}", None, before, after,
        old_context, old_context, partial=False, retry="contrato inicial volta a publicar",
        severity="média", duplication="sem entrega da série rejeitada",
        loss="cotação da outra série descartada por contrato",
        publication="transição rejeitada; contrato inicial publicado após retorno",
    )


@pytest.mark.parametrize("seconds,attributed", [(29, 100), (30, 100), (31, 0)])
def test_continuity_boundary_preserves_volume_contract(
    transaction, capsys, record_property, seconds, attributed,
):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    old_context = context_image(previous)
    clock.current += timedelta(seconds=seconds)
    workbook.publish(quote(clock, price=180_060, volume=1100))
    current = collector.get_data()
    output = assert_publication(pipeline, current, clock, capsys)
    assert ("PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE" in output) is (seconds == 31)
    assert ("reason=PROFIT_QUOTE_INTERVAL_EXCEEDED" in output) is (seconds == 31)
    assert collector.last_profit_rtd_receipt.baseline_reset is (seconds == 31)
    assert_attributed_volume(current, attributed)
    assert_attributed_volume(previous, 0)
    assert collector._primary_chart_volume == 1000 + attributed
    assert collector.last_valid_volume == 1100
    assert_detached(previous, current, collector, old_context)
    record_transition(
        record_property, f"intervalo de {seconds}s", None, before, state_image(collector, rtd),
        old_context, context_image(previous), partial=False,
        retry="não aplicável; ciclo entregue", severity="média",
        duplication="replay não exercitado neste caso",
        loss="volume indeterminado não atribuído" if seconds == 31 else "delta atribuído",
        publication="contexto entregue",
    )


@pytest.mark.parametrize("use_new_snapshot", [False, True], ids=["mesma", "nova"])
def test_auxiliary_failure_before_builders_allows_retry(
    transaction, monkeypatch, capsys, record_property, use_new_snapshot,
):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    old_context = context_image(previous)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    injected = InjectedFailure("gravacao no recorder auxiliar em preparacao")
    observer = Mock(side_effect=injected)
    recorder = collector.profit_rtd_validation_recorder
    with monkeypatch.context() as fault:
        fault.setattr(type(recorder), "record", observer)
        assert collector.get_data() is None
    observer.assert_called_once()
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    after = state_image(collector, rtd)
    assert {key for key in before if before[key] != after[key]} == {"recovery"}
    assert after["recovery"] == (True, "PROFIT_QUOTE_AUXILIARY_FAILED")
    assert context_image(previous) == old_context
    if use_new_snapshot:
        clock.current += timedelta(seconds=1)
        pending = quote(clock, price=180_080, volume=1200)
    workbook.publish(pending)
    output = assert_publication(pipeline, collector.get_data(), clock, capsys)
    assert "reason=PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert collector._primary_chart_volume == 1000
    assert not collector._primary_gap_pending
    record_transition(
        record_property, "recorder auxiliar preparado", injected, before, after,
        old_context, old_context, partial=False, retry="recuperação publicada",
        severity="média", duplication="nenhuma na tentativa exercitada",
        loss="volume indeterminado da lacuna não atribuído",
        publication="falha sem publicação; retry publicado",
    )
