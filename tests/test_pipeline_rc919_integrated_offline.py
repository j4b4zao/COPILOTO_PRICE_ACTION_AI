"""Validação integrada RC9.19 com workbook e relógios sintéticos."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import Mock

import pytest

from tests.test_pipeline_rc917_freshness_adversarial import (
    PROTECTED_NOW,
    assert_buy_and_alert,
    offline_chain,
    protected_chain,
)
from tests.test_pipeline_rc918_integrated_offline import make_collector, market_state, row


def publish(workbook, collector, clock, **fields):
    values = row(clock.current, **fields)
    values[14:] = [values[9] - 200, 200]
    workbook.publish(values)
    return collector.get_data()


def state(collector, pipeline, previous):
    return (
        market_state(collector),
        deepcopy(collector.order_flow),
        deepcopy(vars(collector.source_guard)),
        deepcopy(pipeline._temporal_primary_history._entries),
        tuple(pipeline._temporal_processed_contexts),
        deepcopy((previous.decision, previous.alert)),
    )


def assert_published(pipeline, context, clock, capsys):
    assert context.received_timestamp == clock.current
    assert_buy_and_alert(pipeline, context, clock, capsys)


@pytest.mark.parametrize(
    "scenario,reason,marks_gap",
    [
        ("B-maxima", "PROFIT_QUOTE_INCONSISTENT_READ", True),
        ("C-minima", "PROFIT_QUOTE_INCONSISTENT_READ", True),
        ("D-adx", "PROFIT_QUOTE_INCONSISTENT_READ", True),
        ("E-leitura", "PROFIT_QUOTE_READ_ERROR", True),
        ("I-WIN", "TEMPORAL_CONTRACT_TRANSITION_BLOCKED", False),
        ("J-WDO", "TEMPORAL_CONTRACT_TRANSITION_BLOCKED", False),
        ("K-recepcao", "TEMPORAL_VALIDATION_ERROR", False),
        ("L-origem", "TEMPORAL_SOURCE_TIMEZONE_REQUIRED", False),
    ],
)
def test_rejeicao_e_recuperacao_sem_reutilizar_alerta(
    monkeypatch, protected_chain, capsys, scenario, reason, marks_gap,
):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    symbol = "WDOZ26" if scenario == "J-WDO" else "WINZ26"
    previous = publish(workbook, collector, clock, symbol=symbol)
    assert_published(pipeline, previous, clock, capsys)
    old_alert = previous.alert
    engines = {
        type(engine).__name__: engine for engine in pipeline.engines
        if type(engine).__name__ in {"DecisionEngine", "AlertManager"}
    }
    assert set(engines) == {"DecisionEngine", "AlertManager"}
    for engine in engines.values():
        monkeypatch.setattr(engine, "executar", Mock(wraps=engine.executar))

    clock.current += timedelta(seconds=1)
    received = clock.current
    candidate = row(received, symbol=symbol, price=180_060, volume=1500)
    if scenario in {"B-maxima", "C-minima", "D-adx"}:
        second = candidate.copy()
        second[{"B-maxima": 5, "C-minima": 6, "D-adx": 11}[scenario]] = 42
        workbook.publish(candidate, second)
    elif scenario == "E-leitura":
        workbook.rows = iter((None,))
    else:
        if scenario in {"I-WIN", "J-WDO"}:
            candidate[0] = symbol[:3] + "G27"
            candidate[10] = "17/02/2027"
        elif scenario == "K-recepcao":
            clock.current = received.replace(tzinfo=None)
        else:
            candidate[2] = received.time().isoformat()
        workbook.publish(candidate)

    before = state(collector, pipeline, previous)
    assert not collector._primary_gap_pending
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert f"[DATA REJECTED] {reason}" in output
    assert "PROFIT_QUOTE_ACCEPTED" not in output
    assert "BUY" not in output and "SELL" not in output
    assert state(collector, pipeline, previous) == before
    assert pipeline.context is previous
    assert collector._primary_gap_pending is marks_gap
    for engine in engines.values():
        engine.executar.assert_not_called()

    clock.current = received + timedelta(seconds=1)
    recovered = publish(workbook, collector, clock, symbol=symbol, price=180_060, volume=1500)
    assert recovered is not previous
    assert_published(pipeline, recovered, clock, capsys)
    assert recovered.alert is not old_alert
    assert recovered.alert.timestamp != old_alert.timestamp
    assert not collector._primary_gap_pending
    for engine in engines.values():
        engine.executar.assert_called_once_with(recovered)

    assert pipeline.executar(previous) is previous
    assert previous.decision.action == "WAIT"
    assert not previous.alert.valid
    assert capsys.readouterr().out == ""
    for engine in engines.values():
        engine.executar.assert_called_once_with(recovered)


def test_a_snapshot_consistente_com_volume_em_todas_as_fronteiras(
    monkeypatch, protected_chain, capsys,
):
    clock, pipeline = protected_chain
    clock.current = PROTECTED_NOW.replace(minute=14, second=55)
    workbook, collector = make_collector(monkeypatch, clock)
    first = publish(workbook, collector, clock)
    assert_published(pipeline, first, clock, capsys)
    clock.current += timedelta(seconds=5)
    second = publish(workbook, collector, clock, price=180_040, volume=1030)
    assert second.source_timestamp == clock.current.isoformat()
    assert second.multi_timeframe is collector.multi_timeframe
    assert second.market is collector.renko.market
    assert workbook.block_reads == 4
    for tf in ("M1", "M5", "M15"):
        market = collector.multi_timeframe.get(tf)
        assert market.candle_count == 2
        assert market.last_candle.timestamp == clock.current
        assert market.last_candle.volume == 30
    assert [c.volume for c in second.market.candles] == [30, 0, 0]
    assert_published(pipeline, second, clock, capsys)


@pytest.mark.parametrize("read_failure", [True, False], ids=["F-falha", "G-lacuna"])
def test_rebase_e_movimento_renko_observado(monkeypatch, protected_chain, capsys, read_failure):
    clock, pipeline = protected_chain
    clock.current = PROTECTED_NOW.replace(minute=14, second=55)
    workbook, collector = make_collector(monkeypatch, clock)
    first = publish(workbook, collector, clock)
    assert_published(pipeline, first, clock, capsys)
    clock.current += timedelta(seconds=1)
    prior = publish(workbook, collector, clock, price=180_020, volume=1010)
    assert_published(pipeline, prior, clock, capsys)
    if read_failure:
        before = state(collector, pipeline, prior)
        workbook.rows = iter((None,))
        assert collector.get_data() is None
        assert state(collector, pipeline, prior) == before
        assert "PROFIT_QUOTE_READ_ERROR" in capsys.readouterr().out
        assert collector._primary_gap_pending
        clock.current += timedelta(seconds=4)
    else:
        clock.current += timedelta(seconds=65)

    recovered = publish(workbook, collector, clock, price=180_080, volume=1500)
    assert "PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE" in capsys.readouterr().out
    assert recovered.source_timestamp == clock.current.isoformat()
    for tf in ("M1", "M5", "M15"):
        candles = list(collector.multi_timeframe.get(tf).candles)
        assert len(candles) == 2
        assert [c.volume for c in candles] == [10, 0]
    bricks = list(recovered.market.candles)
    assert [(b.open, b.close) for b in bricks] == [
        (180_000, 180_020), (180_020, 180_040), (180_040, 180_060),
        (180_060, 180_080), (180_080, 180_080),
    ]
    assert [b.timestamp for b in bricks[1:]] == [clock.current] * 4
    assert [b.volume for b in bricks] == [10, 0, 0, 0, 0]
    assert collector.last_closed_renko_bricks == 3
    assert collector.last_valid_volume == 1500
    assert collector.order_flow.cumulative_buy == 1300
    assert not collector.order_flow.history
    assert_published(pipeline, recovered, clock, capsys)

    clock.current += timedelta(seconds=1)
    fresh = publish(workbook, collector, clock, price=180_100, volume=1512)
    assert all(collector.multi_timeframe.get(tf).last_candle.volume == 12
               for tf in ("M1", "M5", "M15"))
    assert list(collector.order_flow.history) == [12]
    assert_published(pipeline, fresh, clock, capsys)


def test_m_mistura_estavel_permanece_indetectavel(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    first = publish(workbook, collector, clock)
    assert_published(pipeline, first, clock, capsys)
    clock.current += timedelta(seconds=1)
    new_generation = row(clock.current, price=180_060, volume=1040)
    mixed = new_generation.copy()
    mixed[3] = first.market.last_price
    workbook.publish(mixed, mixed.copy())
    context = collector.get_data()
    assert context.market.last_price == 180_000
    assert context.market.last_candle.volume == 40
    assert context.source_timestamp == clock.current.isoformat()
    assert_published(pipeline, context, clock, capsys)


def test_n_legado_mantem_leitura_e_volume_apos_intervalo(monkeypatch, offline_chain, capsys):
    clock, pipeline = offline_chain
    assert pipeline.temporal_primary_policy is None
    workbook, collector = make_collector(monkeypatch, clock, protected=False)
    assert collector.temporal_primary_policy is None
    first = publish(workbook, collector, clock)
    assert_published(pipeline, first, clock, capsys)
    clock.current += timedelta(seconds=65)
    context = publish(workbook, collector, clock, price=180_040, volume=1120)
    assert workbook.block_reads == 0
    assert "PROFIT_QUOTE_GAP_VOLUME_INDETERMINATE" not in capsys.readouterr().out
    assert all(collector.multi_timeframe.get(tf).last_candle.volume == 120
               for tf in ("M1", "M5", "M15"))
    assert sum(c.volume for c in context.market.candles) == 120
    assert_published(pipeline, context, clock, capsys)
