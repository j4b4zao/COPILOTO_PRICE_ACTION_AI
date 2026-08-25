"""Offline gate do Profit RTD RC8: feature flag no Collector."""

from types import SimpleNamespace

from market_data.collector import Collector


class FakeExcel:
    def __init__(self):
        self.connected_paths = []
        self.book = object()

    def conectar(self, path):
        self.connected_paths.append(path)
        return True


class FakeReader:
    def __init__(self, payload):
        self.payload = dict(payload)

    def obter_dados(self):
        return dict(self.payload)


class FakePipeline:
    def __init__(self):
        self.calls = []

    def process(self, symbol, *, price):
        self.calls.append((symbol, price))
        return SimpleNamespace(
            symbol=symbol,
            state_updated=False,
            baseline_reset=False,
        )


def payload():
    return {
        "ativo": "WINV26",
        "data": "25/08/2026",
        "hora": "15:30:00",
        "open": 170000.0,
        "high": 170200.0,
        "low": 169900.0,
        "close": 170100.0,
        "volume": 1000.0,
        "agressao_compra": 120.0,
        "agressao_venda": 80.0,
    }


def test_flag_false_preserves_legacy_path():
    pipeline = FakePipeline()
    collector = Collector(
        excel=FakeExcel(),
        reader=FakeReader(payload()),
        enable_profit_rtd_order_flow=False,
        profit_rtd_order_flow_pipeline=pipeline,
        chart_mode="NORMAL",
    )

    result = collector.get_data()

    assert result is not None
    assert pipeline.calls == []
    assert collector.enable_profit_rtd_order_flow is False
    assert collector.order_flow.cumulative_buy == 120.0
    assert collector.order_flow.cumulative_sell == 80.0
    assert collector.order_flow.sampling_mode == "TICK"


def test_flag_true_routes_to_rtd_pipeline_and_skips_legacy_update():
    pipeline = FakePipeline()
    collector = Collector(
        excel=FakeExcel(),
        reader=FakeReader(payload()),
        enable_profit_rtd_order_flow=True,
        profit_rtd_order_flow_pipeline=pipeline,
        chart_mode="NORMAL",
    )

    result = collector.get_data()

    assert result is not None
    assert pipeline.calls == [("WINV26", 170100.0)]
    assert collector.last_profit_rtd_receipt is not None
    # A pipeline fake não altera o estado: isto prova que o caminho legado
    # não foi executado por engano quando a fonte RTD está habilitada.
    assert collector.order_flow.cumulative_buy is None
    assert collector.order_flow.cumulative_sell is None


def test_rtd_pipeline_runs_even_when_primary_snapshot_is_duplicate():
    pipeline = FakePipeline()
    collector = Collector(
        excel=FakeExcel(),
        reader=FakeReader(payload()),
        enable_profit_rtd_order_flow=True,
        profit_rtd_order_flow_pipeline=pipeline,
        chart_mode="NORMAL",
    )

    first = collector.get_data()
    second = collector.get_data()

    assert first is not None
    assert second is None
    assert pipeline.calls == [
        ("WINV26", 170100.0),
        ("WINV26", 170100.0),
    ]


def test_config_default_remains_disabled():
    from config.settings import ENABLE_PROFIT_RTD_ORDER_FLOW

    assert ENABLE_PROFIT_RTD_ORDER_FLOW is False


def main():
    test_flag_false_preserves_legacy_path()
    test_flag_true_routes_to_rtd_pipeline_and_skips_legacy_update()
    test_rtd_pipeline_runs_even_when_primary_snapshot_is_duplicate()
    test_config_default_remains_disabled()
    print("Profit RTD RC8: OK")


if __name__ == "__main__":
    main()
