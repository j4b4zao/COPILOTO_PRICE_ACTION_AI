"""Integracao offline do ciclo protegido RC9.21 com Excel e RTD simulados."""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from core.renko_state import RenkoState
from tests.test_pipeline_rc917_freshness_adversarial import offline_chain, protected_chain
from tests.test_pipeline_rc918_integrated_offline import make_collector
from tests.test_pipeline_rc920_integrated_offline import (
    assert_no_publication,
    assert_publication,
    install_rtd,
)
from tests.test_pipeline_rc920_source_recovery_adversarial import quote
from tests.test_pipeline_rc921_transactional_adversarial import (
    TIMEFRAMES,
    assert_shared,
    context_image,
    state_image,
    transaction,
)


def assert_charts(context, collector, close, volume, bricks):
    assert_shared(context, collector)
    assert collector.last_closed_renko_bricks == bricks
    assert collector.last_new_candles == dict.fromkeys(TIMEFRAMES, False)
    assert [c.close for c in context.market.candles] == [
        *range(180_020, close + 1, 20), close,
    ]
    assert [c.volume for c in context.market.candles] == [volume] + [0] * bricks
    for tf in TIMEFRAMES:
        market = context.multi_timeframe.get(tf)
        assert market.candle_count == 1
        candle = market.last_candle
        assert (candle.open, candle.high, candle.low, candle.close, candle.volume) == (
            180_000, close, 180_000, close, volume,
        )


def assert_retained(previous, image, current):
    assert context_image(previous) == image
    assert previous.market is not current.market
    assert previous.order_flow_state is not current.order_flow_state
    assert previous.multi_timeframe is not current.multi_timeframe
    for tf in TIMEFRAMES:
        old = previous.multi_timeframe.get(tf)
        new = current.multi_timeframe.get(tf)
        assert old is not new
        assert old.last_candle is not new.last_candle


def assert_duplicate(workbook, collector, rtd, pending, capsys):
    accepted = state_image(collector, rtd)
    reads = rtd.reader.read_times_trades.call_count
    workbook.publish(pending)
    assert collector.get_data() is None
    output = assert_no_publication(capsys, "PROFIT_QUOTE_DUPLICATE")
    assert "PROFIT_QUOTE_ACCEPTED" not in output
    assert state_image(collector, rtd) == accepted
    assert rtd.reader.read_times_trades.call_count == reads


@pytest.mark.parametrize("fail_before_return", [False, True], ids=["delivered", "failed"])
def test_prepared_accepted_and_return_are_distinct(
    transaction, monkeypatch, capsys, fail_before_return,
):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    retained = context_image(previous)
    old_adapter, old_dedup = rtd.state_adapter, rtd.deduplicator
    prepare = type(collector)._collect_cycle
    report = collector._report_protected_acceptance
    events = []
    candidate = []
    fault = RuntimeError("falha sintetica entre aceite e retorno")
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)

    def observe_prepared(staged):
        context = prepare(staged)
        assert staged is not collector
        assert_charts(context, staged, 180_060, 100, 3)
        assert context.order_flow_state.cumulative_buy == 1
        assert state_image(collector, rtd) == before
        assert rtd.state_adapter is old_adapter and rtd.deduplicator is old_dedup
        assert_shared(previous, collector)
        assert_retained(previous, retained, context)
        candidate.append(context)
        events.append("PREPARED")
        return context

    def observe_accepted(live, reason):
        assert live is collector
        assert events == ["PREPARED"]
        assert_shared(candidate[0], collector)
        assert collector._last_primary_receipt == clock.current
        assert rtd.state_adapter.state is candidate[0].order_flow_state
        assert rtd.state_adapter is not old_adapter and rtd.deduplicator is not old_dedup
        assert old_adapter.state is previous.order_flow_state
        assert old_dedup._previous == before["rtd"][0]["_previous"]
        assert pipeline.context is previous
        events.append("ACCEPTED")
        report(reason)
        if fail_before_return:
            raise fault

    with monkeypatch.context() as patch:
        patch.setattr(type(collector), "_collect_cycle", observe_prepared)
        patch.setattr(type(collector), "_report_protected_acceptance", observe_accepted)
        delivered = []
        if fail_before_return:
            with pytest.raises(RuntimeError) as raised:
                delivered.append(collector.get_data())
            assert raised.value is fault
            assert not delivered
            events.append("FAILED")
        else:
            delivered.append(collector.get_data())
            assert delivered[0] is candidate[0]
            events.append("DELIVERED")

    assert events == ["PREPARED", "ACCEPTED", "FAILED" if fail_before_return else "DELIVERED"]
    assert pipeline.context is previous
    assert collector.profit_rtd_order_flow_pipeline is rtd
    assert collector.last_profit_rtd_receipt.new_trade_count == 1
    assert collector.last_valid_volume == collector._primary_chart_volume == 1100
    if delivered:
        output = assert_publication(pipeline, delivered[0], clock, capsys)
    else:
        output = capsys.readouterr().out
    assert output.count("PROFIT_QUOTE_ACCEPTED") == 1
    assert output.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert_retained(previous, retained, candidate[0])


@pytest.mark.parametrize("boundary,retry_new", [
    ("M1", False), ("M5", True), ("M15", False), ("Renko", True),
])
def test_mutacao_da_candidata_fica_isolada(transaction, monkeypatch, capsys, boundary, retry_new):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    retained = context_image(previous)
    published = vars(collector)
    fork = type(collector)._fork_protected_cycle
    reached = []
    error = RuntimeError(boundary)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)

    with monkeypatch.context() as patch:
        def inject(live):
            staged = fork(live)
            if boundary == "Renko":
                target, method = staged.renko, "_add_current"
            else:
                target, method = staged.multi_timeframe._builders[boundary], "update"
            mutate = getattr(target, method)

            def fail_after_mutation(*args, **kwargs):
                mutate(*args, **kwargs)
                if boundary == "Renko":
                    assert staged.renko.market.candle_count == 2
                else:
                    assert target.current.close == 180_060
                    assert target.current.volume == 100
                assert vars(collector) is published
                assert state_image(collector, rtd) == before
                assert context_image(previous) == retained
                reached.append(boundary)
                raise error

            patch.setattr(target, method, fail_after_mutation)
            return staged

        patch.setattr(type(collector), "_fork_protected_cycle", inject)
        with pytest.raises(RuntimeError) as raised:
            collector.get_data()
        assert raised.value is error

    assert reached == [boundary]
    output = assert_no_publication(capsys, "PROFIT_QUOTE_ELIGIBLE")
    assert "PROFIT_QUOTE_ACCEPTED" not in output
    assert state_image(collector, rtd) == before
    assert pipeline.context is previous
    assert_shared(previous, collector)

    close, delta, bricks = 180_060, 100, 3
    if retry_new:
        clock.current += timedelta(seconds=1)
        close, delta, bricks = 180_080, 200, 4
        pending = quote(clock, price=close, volume=1000 + delta)
    workbook.publish(pending)
    delivered = collector.get_data()
    assert assert_publication(pipeline, delivered, clock, capsys).count("PROFIT_QUOTE_PUBLISHED") == 1
    assert_charts(delivered, collector, close, delta, bricks)
    assert collector.last_valid_volume == collector._primary_chart_volume == 1000 + delta
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert_retained(previous, retained, delivered)


def test_falha_rtd_preserva_referencias_e_rebaseia_retry(transaction, monkeypatch, capsys):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    before = state_image(collector, rtd)
    retained = context_image(previous)
    adapter, dedup = rtd.state_adapter, rtd.deduplicator
    attempts = []
    build = rtd.aggression_builder.build
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)

    def reject_after_dedup(batch):
        assert batch.new_trade_count == 1
        assert rtd.state_adapter is adapter and rtd.deduplicator is dedup
        assert state_image(collector, rtd) == before
        attempts.append(batch)
        raise OSError("falha auxiliar sintetica")

    with monkeypatch.context() as patch:
        patch.setattr(rtd, "aggression_builder", SimpleNamespace(build=reject_after_dedup))
        workbook.publish(pending)
        assert collector.get_data() is None
    assert len(attempts) == 1
    assert rtd.aggression_builder.build == build
    assert_no_publication(capsys, "PROFIT_QUOTE_AUXILIARY_FAILED")
    assert state_image(collector, rtd) == {
        **before, "recovery": (True, "PROFIT_QUOTE_AUXILIARY_FAILED"),
    }
    assert pipeline.context is previous
    assert rtd.state_adapter is adapter and rtd.deduplicator is dedup

    workbook.publish(pending)
    delivered = collector.get_data()
    output = assert_publication(pipeline, delivered, clock, capsys)
    assert output.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert "reason=PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert collector.profit_rtd_order_flow_pipeline is rtd
    assert rtd.state_adapter.state is delivered.order_flow_state
    assert rtd.state_adapter is not adapter and rtd.deduplicator is not dedup
    assert adapter.state is previous.order_flow_state
    assert collector.last_profit_rtd_receipt.baseline_reset
    assert delivered.order_flow_state.cumulative_buy == 0
    assert collector._primary_chart_volume == 1000
    assert_charts(delivered, collector, 180_060, 0, 3)
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert_retained(previous, retained, delivered)


@pytest.mark.parametrize("initial,symbol,expiry", [
    ("WINZ26", "WDOZ26", "16/12/2026"),
    ("WDOZ26", "WINZ26", "16/12/2026"),
    ("WINZ26", "WING27", "17/02/2027"),
], ids=["WIN-WDO", "WDO-WIN", "rollover"])
def test_transicao_de_contrato_preserva_serie_aceita(
    monkeypatch, protected_chain, capsys, initial, symbol, expiry,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    workbook.publish(quote(clock, symbol=initial))
    previous = collector.get_data()
    assert_publication(pipeline, previous, clock, capsys)
    before = state_image(collector, rtd)
    retained = context_image(previous)

    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, symbol=symbol, expiry=expiry, price=180_040, volume=1500))
    assert collector.get_data() is None
    assert_no_publication(capsys, "TEMPORAL_CONTRACT_TRANSITION_BLOCKED")
    assert state_image(collector, rtd) == before
    assert pipeline.context is previous
    rtd.reader.read_times_trades.assert_called_once()

    clock.current += timedelta(seconds=1)
    workbook.publish(quote(clock, symbol=initial, price=180_060, volume=1100))
    delivered = collector.get_data()
    assert_publication(pipeline, delivered, clock, capsys)
    assert delivered.market.symbol == initial
    assert collector._primary_contract == before["contract"]
    assert_charts(delivered, collector, 180_060, 100, 3)
    assert_retained(previous, retained, delivered)


@pytest.mark.parametrize("seconds,volume", [(29, 100), (30, 100), (31, 0)])
def test_continuidade_e_lacuna_preservam_bases(transaction, capsys, seconds, volume):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    retained = context_image(previous)
    clock.current += timedelta(seconds=seconds)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    delivered = collector.get_data()
    output = assert_publication(pipeline, delivered, clock, capsys)
    gap = seconds > 30
    assert ("reason=PROFIT_QUOTE_INTERVAL_EXCEEDED" in output) is gap
    assert collector.last_profit_rtd_receipt.baseline_reset is gap
    assert delivered.order_flow_state.cumulative_buy == (0 if gap else 1)
    assert collector.last_valid_volume == 1100
    assert collector._primary_chart_volume == 1000 + volume
    assert_charts(delivered, collector, 180_060, volume, 3)
    assert_duplicate(workbook, collector, rtd, pending, capsys)
    assert_retained(previous, retained, delivered)


def test_copia_impossivel_bloqueia_ate_novo_coletor(transaction, monkeypatch, capsys):
    clock, pipeline, workbook, collector, rtd, previous = transaction
    retained = context_image(previous)
    before = state_image(collector, rtd)
    reads = workbook.block_reads, rtd.reader.read_times_trades.call_count
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    reason = "PROFIT_QUOTE_REINITIALIZATION_REQUIRED"

    def refuse_copy(renko, memo):
        assert renko is collector.renko
        raise TypeError("Renko sem copia isolada")

    with monkeypatch.context() as patch:
        patch.setattr(RenkoState, "__deepcopy__", refuse_copy, raising=False)
        with pytest.raises(RuntimeError, match=reason) as raised:
            collector.get_data()
    assert isinstance(raised.value.__cause__, TypeError)
    assert "PROFIT_QUOTE_PUBLISHED" not in capsys.readouterr().out
    assert collector.get_data() is None
    assert_no_publication(capsys, reason)
    clock.current += timedelta(seconds=1)
    newer = quote(clock, price=180_080, volume=1200)
    workbook.publish(newer)
    assert collector.get_data() is None
    assert_no_publication(capsys, reason)
    assert (workbook.block_reads, rtd.reader.read_times_trades.call_count) == reads
    assert state_image(collector, rtd) == {**before, "blocked": True}
    assert pipeline.context is previous

    replacement_workbook, replacement = make_collector(monkeypatch, clock)
    replacement_rtd = install_rtd(replacement, clock)
    replacement_workbook.publish(newer)
    delivered = replacement.get_data()
    assert_publication(pipeline, delivered, clock, capsys)
    assert replacement_rtd is not rtd
    assert replacement.last_profit_rtd_receipt.baseline_reset
    assert replacement.last_valid_volume == replacement._primary_chart_volume == 1200
    assert replacement.last_closed_renko_bricks == 0
    assert delivered.order_flow_state.cumulative_buy == 0
    for market in [delivered.market, *(delivered.multi_timeframe.get(tf) for tf in TIMEFRAMES)]:
        assert market.candle_count == 1
        candle = market.last_candle
        assert (candle.open, candle.close, candle.volume) == (180_080, 180_080, 0)
    assert state_image(collector, rtd) == {**before, "blocked": True}
    assert_retained(previous, retained, delivered)

