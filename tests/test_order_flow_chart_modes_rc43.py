"""Validação offline do Order Flow em gráficos NORMAL e RENKO RC4.3."""

from datetime import datetime, timedelta

from analysis.order_flow import OrderFlow
from enums.chart_mode import ChartMode
from market_data.collector import Collector
from models.result_base import ResultStatus


START = datetime(2026, 8, 21, 10, 0)


class FakeExcel:

    def conectar(self, path):
        return bool(path)


class FakeReader:

    def __init__(self, readings):
        self.readings = list(readings)

    def obter_dados(self):
        if not self.readings:
            return None
        return self.readings.pop(0)


class FakeClock:

    def __init__(self, amount):
        self.timestamps = [
            START + timedelta(seconds=index)
            for index in range(amount)
        ]

    def now(self):
        return self.timestamps.pop(0)


def readings(prices, buy_step=20.0, sell_step=100.0):
    values = []
    cumulative_buy = 1000.0
    cumulative_sell = 1000.0

    for index, price in enumerate(prices):
        if index:
            cumulative_buy += buy_step
            cumulative_sell += sell_step

        values.append({
            "ativo": "WINV26",
            "close": price,
            "volume": 1000.0 + index * 100.0,
            "agressao_compra": cumulative_buy,
            "agressao_venda": cumulative_sell,
        })

    return values


def collector(mode, prices, buy_step=20.0, sell_step=100.0):
    data = readings(prices, buy_step, sell_step)
    return Collector(
        excel=FakeExcel(),
        reader=FakeReader(data),
        clock=FakeClock(len(data)),
        chart_mode=mode,
        renko_brick_size=20.0,
    )


def collect_all(instance, amount):
    context = None
    for _ in range(amount):
        context = instance.get_data()
    return context


def teste_normal_amostra_cada_leitura_valida():
    prices = (100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0)
    instance = collector("NORMAL", prices)
    context = collect_all(instance, len(prices))

    assert instance.chart_mode == ChartMode.NORMAL
    assert instance.order_flow.sampling_mode == "TICK"
    assert instance.order_flow.sample_count == 6
    assert instance.order_flow.pattern_ready is True

    OrderFlow().executar(context)

    assert context.order_flow.patterns_ready is True
    assert context.order_flow.divergence == "PRICE_UP_DELTA_DOWN"


def teste_renko_ignora_ruido_interno_do_tijolo():
    prices = (100.0, 105.0, 110.0, 115.0, 119.0, 118.0)
    instance = collector("RENKO", prices)
    context = collect_all(instance, len(prices))

    assert instance.chart_mode == ChartMode.RENKO
    assert instance.last_closed_renko_bricks == 0
    assert instance.order_flow.sample_count == 0
    assert instance.order_flow.waiting_for_sample is True

    OrderFlow().executar(context)

    assert context.order_flow.status == ResultStatus.SKIPPED
    assert "ORDER_FLOW_WAITING_RENKO_CLOSE" in context.order_flow.reasons
    assert context.order_flow.divergence == "INSUFFICIENT_DATA"


def teste_renko_consolida_agressao_no_fechamento():
    prices = (100.0, 105.0, 110.0, 115.0, 119.0, 120.0)
    instance = collector("RENKO", prices)
    context = collect_all(instance, len(prices))

    assert instance.last_closed_renko_bricks == 1
    assert instance.order_flow.sample_count == 1
    assert instance.order_flow.delta == -400.0
    assert instance.order_flow.sampling_mode == "RENKO_CLOSE"
    assert instance.order_flow.source_units == 1

    OrderFlow().executar(context)

    assert context.order_flow.valid is True
    assert context.order_flow.patterns_ready is False


def teste_varios_tijolos_geram_uma_amostra_agregada():
    prices = (100.0, 165.0)
    instance = collector("RENKO", prices)
    collect_all(instance, len(prices))

    assert instance.last_closed_renko_bricks == 3
    assert instance.order_flow.sample_count == 1
    assert instance.order_flow.source_units == 3


def teste_renko_libera_padrao_so_apos_seis_fechamentos():
    prices = (100.0, 120.0, 140.0, 160.0, 180.0, 200.0, 220.0)
    instance = collector("RENKO", prices)
    context = collect_all(instance, len(prices))

    assert instance.order_flow.sample_count == 6
    assert instance.order_flow.pattern_ready is True

    OrderFlow().executar(context)

    assert context.order_flow.patterns_ready is True
    assert context.order_flow.divergence == "PRICE_UP_DELTA_DOWN"
    assert context.order_flow.sampling_mode == "RENKO_CLOSE"


def teste_normal_e_renko_nao_alteram_decisao_por_order_flow():
    prices = (100.0, 120.0, 140.0, 160.0, 180.0, 200.0, 220.0)

    for mode in ("NORMAL", "RENKO"):
        instance = collector(mode, prices)
        context = collect_all(instance, len(prices))
        decision_before = context.decision.action
        score_before = context.score.total

        OrderFlow().executar(context)

        assert context.decision.action == decision_before
        assert context.score.total == score_before


if __name__ == "__main__":
    tests = (
        teste_normal_amostra_cada_leitura_valida,
        teste_renko_ignora_ruido_interno_do_tijolo,
        teste_renko_consolida_agressao_no_fechamento,
        teste_varios_tijolos_geram_uma_amostra_agregada,
        teste_renko_libera_padrao_so_apos_seis_fechamentos,
        teste_normal_e_renko_nao_alteram_decisao_por_order_flow,
    )

    for test in tests:
        test()

    print("OK - Order Flow chart modes RC4.3")
