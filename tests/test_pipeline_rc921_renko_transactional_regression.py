"""Contratos Renko protegidos após o isolamento transacional RC9.21."""

from datetime import timedelta

import pytest

from core.renko_state import RenkoState
from tests.test_pipeline_rc917_freshness_adversarial import offline_chain, protected_chain
from tests.test_pipeline_rc918_integrated_offline import make_collector
from tests.test_pipeline_rc920_integrated_offline import assert_publication, install_rtd
from tests.test_pipeline_rc920_source_recovery_adversarial import quote
from tests.test_pipeline_rc921_transactional_adversarial import (
    TIMEFRAMES,
    InjectedFailure,
    context_image,
    state_image,
)


@pytest.fixture
def published_renko(monkeypatch, protected_chain, capsys):
    clock, pipeline = protected_chain
    clock.current += timedelta(minutes=14, seconds=59)
    workbook, collector = make_collector(monkeypatch, clock)
    rtd = install_rtd(collector, clock)
    workbook.publish(quote(clock))
    previous = collector.get_data()
    assert_publication(pipeline, previous, clock, capsys)
    assert collector.last_closed_renko_bricks == 0
    assert all(previous.multi_timeframe.get(tf).candle_count == 1 for tf in TIMEFRAMES)
    return clock, pipeline, workbook, collector, rtd, previous


@pytest.mark.parametrize("boundary", ["antes", "durante"])
@pytest.mark.parametrize("retry", ["mesma", "nova"])
def test_renko_failure_preserves_publication_and_retry_attributes_volume_once(
    published_renko, monkeypatch, capsys, boundary, retry,
):
    clock, pipeline, workbook, collector, rtd, previous = published_renko
    before = state_image(collector, rtd)
    retained = context_image(previous)
    markets = tuple(previous.multi_timeframe.get(tf) for tf in TIMEFRAMES)
    renko = collector.renko
    fault = InjectedFailure(f"falha {boundary} do Renko")
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    original_add_current = RenkoState._add_current
    reached = []

    def fail_at_renko_entry(candidate, **tick):
        reached.append(candidate.market.candle_count)
        assert candidate is not renko
        assert state_image(collector, rtd) == before
        raise fault

    def fail_after_first_brick(candidate, *args, **kwargs):
        original_add_current(candidate, *args, **kwargs)
        reached.append(candidate.market.candle_count)
        assert candidate is not renko
        assert state_image(collector, rtd) == before
        raise fault

    with monkeypatch.context() as inject:
        if boundary == "antes":
            inject.setattr(RenkoState, "update_tick", fail_at_renko_entry)
        else:
            inject.setattr(RenkoState, "_add_current", fail_after_first_brick)
        with pytest.raises(InjectedFailure) as raised:
            collector.get_data()
        assert raised.value is fault

    assert reached == ([1] if boundary == "antes" else [2])
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_ELIGIBLE" in output
    assert "PROFIT_QUOTE_ACCEPTED" not in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert state_image(collector, rtd) == before
    assert pipeline.context is previous
    assert context_image(previous) == retained
    assert collector.renko is renko and previous.market is renko.market
    assert all(collector.multi_timeframe.get(tf) is market
               for tf, market in zip(TIMEFRAMES, markets))
    assert all(market.candle_count == 1 for market in markets)
    assert renko.market.candle_count == 1
    assert collector.last_closed_renko_bricks == 0
    assert not collector._primary_publication_blocked

    expected_close, expected_volume = 180_060, 100
    if retry == "nova":
        clock.current += timedelta(seconds=1)
        expected_close, expected_volume = 180_080, 200
        pending = quote(clock, price=expected_close, volume=1000 + expected_volume)
    workbook.publish(pending)
    recovered = collector.get_data()
    output = assert_publication(pipeline, recovered, clock, capsys)
    assert output.count("PROFIT_QUOTE_PUBLISHED") == 1
    assert context_image(previous) == retained
    assert recovered.market is collector.renko.market
    assert recovered.market is not previous.market
    assert recovered.multi_timeframe is not previous.multi_timeframe
    assert recovered.order_flow_state is not previous.order_flow_state
    assert collector.last_new_candles == dict.fromkeys(TIMEFRAMES, True)
    for tf in TIMEFRAMES:
        current_market = recovered.multi_timeframe.get(tf)
        assert current_market.candle_count == 2
        assert (current_market.last_candle.close, current_market.last_candle.volume) == (
            expected_close, expected_volume,
        )
        assert sum(candle.volume for candle in current_market.candles) == expected_volume

    closed = (expected_close - 180_000) // 20
    closes = list(range(180_020, expected_close + 1, 20)) + [expected_close]
    assert collector.last_closed_renko_bricks == closed
    assert recovered.market.candle_count == closed + 1
    assert [candle.close for candle in recovered.market.candles] == closes
    assert [candle.volume for candle in recovered.market.candles] == [expected_volume] + [0] * closed

    committed = state_image(collector, rtd)
    workbook.publish(pending)
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_DUPLICATE" in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert state_image(collector, rtd) == committed
    assert context_image(previous) == retained


def test_renko_copy_failure_requires_explicit_new_collector(
    published_renko, monkeypatch, capsys,
):
    clock, pipeline, workbook, collector, rtd, previous = published_renko
    before = state_image(collector, rtd)
    retained = context_image(previous)
    quote_reads = workbook.block_reads
    rtd_reads = rtd.reader.read_times_trades.call_count
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)

    def fail_copy(candidate, _memo):
        assert candidate is collector.renko
        raise TypeError("Renko sem cópia isolada")

    with monkeypatch.context() as inject:
        inject.setattr(RenkoState, "__deepcopy__", fail_copy, raising=False)
        with pytest.raises(RuntimeError, match="PROFIT_QUOTE_REINITIALIZATION_REQUIRED") as raised:
            collector.get_data()
    assert isinstance(raised.value.__cause__, TypeError)
    assert "Renko sem cópia isolada" in str(raised.value.__cause__)
    assert state_image(collector, rtd) == {**before, "blocked": True}
    assert context_image(previous) == retained
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_REINITIALIZATION_REQUIRED" in capsys.readouterr().out
    clock.current += timedelta(seconds=1)
    newer = quote(clock, price=180_080, volume=1200)
    workbook.publish(newer)
    assert collector.get_data() is None
    output = capsys.readouterr().out
    assert "PROFIT_QUOTE_REINITIALIZATION_REQUIRED" in output
    assert "PROFIT_QUOTE_PUBLISHED" not in output
    assert workbook.block_reads == quote_reads
    assert rtd.reader.read_times_trades.call_count == rtd_reads

    new_workbook, replacement = make_collector(monkeypatch, clock)
    install_rtd(replacement, clock)
    new_workbook.publish(newer)
    recovered = replacement.get_data()
    assert_publication(pipeline, recovered, clock, capsys)
    assert recovered.market is not previous.market
    assert replacement.last_closed_renko_bricks == 0
    assert replacement.last_profit_rtd_receipt.baseline_reset
    for market in [recovered.market, *(recovered.multi_timeframe.get(tf) for tf in TIMEFRAMES)]:
        assert market.candle_count == 1
        candle = market.last_candle
        assert (candle.open, candle.close, candle.volume) == (180_080, 180_080, 0)
    assert state_image(collector, rtd) == {**before, "blocked": True}
    assert context_image(previous) == retained
