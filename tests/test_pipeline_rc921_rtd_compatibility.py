"""Compatibilidade offline da referência RTD com versões isoladas do Collector."""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from tests.test_pipeline_rc917_freshness_adversarial import offline_chain, protected_chain
from tests.test_pipeline_rc918_integrated_offline import make_collector
from tests.test_pipeline_rc920_integrated_offline import assert_publication, install_rtd
from tests.test_pipeline_rc920_source_recovery_adversarial import quote
from tests.test_pipeline_rc921_transactional_adversarial import context_image


def test_injected_rtd_keeps_identity_and_reads_only_accepted_state(
    monkeypatch, protected_chain, capsys,
):
    clock, analysis = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    original = install_rtd(collector, clock)
    read = original.reader.read_times_trades.side_effect
    baseline_trade = read("WINZ26")["trades"][0]
    workbook.publish(quote(clock))
    previous = collector.get_data()
    assert_publication(analysis, previous, clock, capsys)
    retained_context = context_image(previous)
    accepted_dedup = original.deduplicator
    accepted_adapter = original.state_adapter
    assert collector.profit_rtd_order_flow_pipeline is original
    assert accepted_dedup._previous
    assert accepted_adapter.state is previous.order_flow_state
    assert (accepted_adapter._cumulative_buy, accepted_adapter._cumulative_sell) == (0, 0)

    def overlapping_window(symbol):
        payload = read(symbol)
        payload["trades"].append(baseline_trade)
        return payload

    original.reader = SimpleNamespace(read_times_trades=overlapping_window)
    build = original.aggression_builder.build
    attempts = []

    def build_with_fault(batch):
        assert collector.profit_rtd_order_flow_pipeline is original
        assert original.deduplicator is accepted_dedup
        assert original.state_adapter is accepted_adapter
        assert context_image(previous) == retained_context
        attempts.append(batch)
        if len(attempts) == 1:
            raise OSError("falha auxiliar sintética após deduplicação")
        return build(batch)

    original.aggression_builder = SimpleNamespace(build=build_with_fault)
    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_AUXILIARY_FAILED" in capsys.readouterr().out
    assert attempts[0].new_trade_count == 1
    assert original.deduplicator is accepted_dedup
    assert original.state_adapter is accepted_adapter
    assert context_image(previous) == retained_context

    workbook.publish(pending)
    recovered = collector.get_data()
    output = assert_publication(analysis, recovered, clock, capsys)
    assert "reason=PROFIT_QUOTE_AUXILIARY_FAILED" in output
    assert collector.profit_rtd_order_flow_pipeline is original
    assert original.reader.read_times_trades is overlapping_window
    assert original.aggression_builder.build is build_with_fault
    assert attempts[1].baseline_only
    assert original.deduplicator._previous != accepted_dedup._previous
    assert original.state_adapter is not accepted_adapter
    assert original.state_adapter.state is recovered.order_flow_state
    assert original.state_adapter.state.cumulative_buy == 0
    assert context_image(previous) == retained_context
    assert collector._primary_chart_volume == 1000
    workbook.publish(pending)
    assert collector.get_data() is None
    assert "PROFIT_QUOTE_DUPLICATE" in capsys.readouterr().out
    assert len(attempts) == 2


class AlternateRTD:
    """Composição pelo protocolo prepare/publish, sem herdar métodos privados."""

    def __init__(self, implementation):
        self.implementation = implementation

    @property
    def reader(self):
        return self.implementation.reader

    @property
    def state_adapter(self):
        return self.implementation.state_adapter

    def prepare(self, symbol, *, price, rebase):
        return self.implementation.prepare(symbol, price=price, rebase=rebase)

    def publish(self, staged):
        self.implementation.publish(staged)


def test_alternate_pipeline_without_private_fork_publishes_and_retries(
    monkeypatch, protected_chain, capsys,
):
    clock, analysis = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    implementation = install_rtd(collector, clock)
    original = AlternateRTD(implementation)
    collector.profit_rtd_order_flow_pipeline = original
    assert not hasattr(original, "_fork")
    workbook.publish(quote(clock))
    previous = collector.get_data()
    assert_publication(analysis, previous, clock, capsys)
    retained = context_image(previous)
    accepted = collector.profit_rtd_order_flow_pipeline
    assert accepted.reader is original.reader
    assert accepted.state_adapter.state is previous.order_flow_state
    assert implementation.deduplicator._previous == ()

    clock.current += timedelta(seconds=1)
    pending = quote(clock, price=180_060, volume=1100)
    workbook.publish(pending)
    with monkeypatch.context() as patch:
        patch.setattr(accepted.reader.read_times_trades, "side_effect", OSError("RTD offline"))
        assert collector.get_data() is None
        assert collector.profit_rtd_order_flow_pipeline is accepted
        assert context_image(previous) == retained
    assert "PROFIT_QUOTE_AUXILIARY_FAILED" in capsys.readouterr().out

    workbook.publish(pending)
    recovered = collector.get_data()
    assert_publication(analysis, recovered, clock, capsys)
    current = collector.profit_rtd_order_flow_pipeline
    assert current.state_adapter.state is recovered.order_flow_state
    assert current.implementation.deduplicator._previous != accepted.implementation.deduplicator._previous
    assert collector.last_profit_rtd_receipt.baseline_reset
    assert context_image(previous) == retained


def test_alternate_that_cannot_be_isolated_fails_closed(monkeypatch, protected_chain, capsys):
    class NonCopyableRTD(AlternateRTD):
        def __deepcopy__(self, memo):
            return self

    clock, _ = protected_chain
    workbook, collector = make_collector(monkeypatch, clock)
    original = NonCopyableRTD(install_rtd(collector, clock))
    collector.profit_rtd_order_flow_pipeline = original
    workbook.publish(quote(clock))
    with pytest.raises(RuntimeError, match="PROFIT_QUOTE_REINITIALIZATION_REQUIRED") as failure:
        collector.get_data()
    assert str(failure.value.__cause__) == "RTD_PIPELINE_ISOLATION_REQUIRED"
    assert collector.get_data() is None
    assert collector.profit_rtd_order_flow_pipeline is original
    assert not workbook.block_reads
    assert "PROFIT_QUOTE_PUBLISHED" not in capsys.readouterr().out
