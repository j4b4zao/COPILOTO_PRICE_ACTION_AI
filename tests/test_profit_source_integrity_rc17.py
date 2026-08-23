from datetime import datetime

from core.order_flow_state import OrderFlowState
from market_data.collector import Collector
from market_data.profit_source_integrity import ProfitSourceIntegrityGuard


class FakeExcel:
    def conectar(self, _path):
        return True


class SequenceReader:
    def __init__(self, rows):
        self.rows = list(rows)
        self.index = 0

    def obter_dados(self):
        row = self.rows[min(self.index, len(self.rows) - 1)]
        self.index += 1
        return dict(row)


class FixedClock:
    @staticmethod
    def now():
        return datetime(2026, 8, 24, 10, 0, 0)


def row(**updates):
    value = {
        "ativo": "WINV26", "data": "24/08/2026", "hora": "10:00:00",
        "close": 171000.0, "volume": 1000.0,
        "agressao_compra": 500.0, "agressao_venda": 400.0,
    }
    value.update(updates)
    return value


def build(rows):
    return Collector(
        excel=FakeExcel(), reader=SequenceReader(rows), order_flow_state=OrderFlowState(),
        chart_mode="NORMAL", clock=FixedClock,
    )


def test_guard_first_snapshot_is_new():
    decision = ProfitSourceIntegrityGuard().inspect(row())
    assert decision.duplicate is False
    assert decision.symbol_changed is False


def test_guard_exact_repeat_is_duplicate():
    guard = ProfitSourceIntegrityGuard(); guard.inspect(row())
    assert guard.inspect(row()).duplicate is True


def test_guard_volume_change_is_new_snapshot():
    guard = ProfitSourceIntegrityGuard(); guard.inspect(row())
    assert guard.inspect(row(volume=1001.0)).duplicate is False


def test_guard_aggression_change_is_new_snapshot():
    guard = ProfitSourceIntegrityGuard(); guard.inspect(row())
    assert guard.inspect(row(agressao_compra=501.0)).duplicate is False


def test_guard_detects_symbol_change():
    guard = ProfitSourceIntegrityGuard(); guard.inspect(row())
    decision = guard.inspect(row(ativo="WINZ26"))
    assert decision.symbol_changed is True
    assert decision.symbol == "WINZ26"


def test_duplicate_snapshot_does_not_create_second_market_tick():
    collector = build([row(), row()])
    first = collector.get_data()
    count = first.market.candle_count
    second = collector.get_data()
    assert second is None
    assert collector.market.candle_count == count
    assert collector.order_flow.waiting_for_sample is True
    assert collector.order_flow.sampling_mode == "SOURCE_UNCHANGED"


def test_new_aggression_snapshot_produces_real_delta():
    collector = build([
        row(),
        row(hora="10:00:01", volume=1010.0, agressao_compra=508.0, agressao_venda=403.0),
    ])
    collector.get_data(); context = collector.get_data()
    assert context is not None
    assert collector.order_flow.ready is True
    assert collector.order_flow.buy_aggression == 8.0
    assert collector.order_flow.sell_aggression == 3.0
    assert collector.order_flow.delta == 5.0


def test_duplicate_does_not_append_synthetic_zero_delta():
    second = row(hora="10:00:01", volume=1010.0, agressao_compra=508.0, agressao_venda=403.0)
    collector = build([row(), second, second])
    collector.get_data(); collector.get_data()
    samples = collector.order_flow.sample_count
    collector.get_data()
    assert collector.order_flow.sample_count == samples


def test_symbol_change_clears_previous_order_flow_history():
    collector = build([
        row(),
        row(hora="10:00:01", volume=1010.0, agressao_compra=508.0, agressao_venda=403.0),
        row(ativo="WINZ26", hora="10:00:02", volume=100.0, agressao_compra=50.0, agressao_venda=40.0),
    ])
    collector.get_data(); collector.get_data()
    assert collector.order_flow.sample_count == 1
    collector.get_data()
    assert collector.order_flow.sample_count == 0
    assert collector.order_flow.cumulative_buy == 50.0
    assert collector.order_flow.cumulative_sell == 40.0
    assert collector.order_flow.ready is False


def test_missing_aggression_remains_explicitly_unavailable():
    collector = build([row(agressao_compra=None, agressao_venda=None)])
    context = collector.get_data()
    assert context is not None
    assert collector.order_flow.available is False
    assert collector.order_flow.ready is False
