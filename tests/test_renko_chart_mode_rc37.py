"""
Testes offline das opções NORMAL e RENKO RC3.7.
"""

from datetime import datetime, timedelta

from core.renko_state import RenkoState
from enums.chart_mode import ChartMode
from market_data.collector import Collector


START = datetime(2026, 8, 21, 10, 0)


class FakeExcel:

    def conectar(self, path):

        return bool(path)


class FakeReader:

    def __init__(self, prices):

        self.readings = [
            {
                "ativo": "WINV26",
                "close": price,
                "volume": 1000.0 + index * 100.0,
            }
            for index, price in enumerate(prices)
        ]

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


def create_collector(mode, prices, brick_size=20.0):

    return Collector(
        excel=FakeExcel(),
        reader=FakeReader(prices),
        clock=FakeClock(len(prices)),
        chart_mode=mode,
        renko_brick_size=brick_size,
    )


def collect_all(collector, amount):

    context = None

    for _ in range(amount):

        context = collector.get_data()

    return context


def teste_normal_permanece_padrao_temporal():

    prices = (100.0, 105.0, 110.0)
    collector = create_collector("NORMAL", prices)
    context = collect_all(collector, len(prices))

    assert collector.chart_mode == ChartMode.NORMAL
    assert context.market is collector.multi_timeframe.primary
    assert context.market.timeframe == "M1"
    assert context.market.candle_count == 1
    assert collector.renko.market.candle_count == 0


def teste_renko_e_mercado_principal_configuravel():

    prices = (100.0, 110.0, 120.0, 140.0, 135.0)
    collector = create_collector("RENKO", prices, brick_size=20.0)
    context = collect_all(collector, len(prices))

    assert collector.chart_mode == ChartMode.RENKO
    assert context.market is collector.renko.market
    assert context.market.timeframe == "RENKO_20"
    assert context.market.candle_count == 3

    candles = context.market.candles.all()

    assert candles[0].open == 100.0
    assert candles[0].close == 120.0
    assert candles[1].open == 120.0
    assert candles[1].close == 140.0
    assert candles[2].open == 140.0
    assert candles[2].close == 135.0


def teste_renko_fecha_varios_tijolos_no_mesmo_tick():

    state = RenkoState(brick_size=20.0)

    state.update_tick(
        symbol="WINV26",
        price=100.0,
        cumulative_volume=1000.0,
        timestamp=START,
    )

    closed = state.update_tick(
        symbol="WINV26",
        price=165.0,
        cumulative_volume=1500.0,
        timestamp=START + timedelta(seconds=1),
    )

    assert closed == 3
    assert state.market.candle_count == 4

    candles = state.market.candles.all()

    assert [candle.close for candle in candles] == [
        120.0,
        140.0,
        160.0,
        165.0,
    ]


def teste_contexto_temporal_continua_disponivel_no_renko():

    prices = (100.0, 120.0, 140.0)
    collector = create_collector("RENKO", prices)
    context = collect_all(collector, len(prices))

    assert context.market.timeframe == "RENKO_20"
    assert context.multi_timeframe is collector.multi_timeframe
    assert context.multi_timeframe.get("M1").candle_count == 1
    assert context.multi_timeframe.get("M5").candle_count == 1
    assert context.multi_timeframe.get("M15").candle_count == 1


def teste_configuracoes_invalidas_sao_rejeitadas():

    for mode in ("RANGE", "", None):

        if mode is None:

            continue

        try:

            ChartMode.normalize(mode)

        except ValueError:

            continue

        raise AssertionError(
            "Modo de gráfico inválido deveria ser rejeitado."
        )

    for size in (0.0, -20.0, float("inf")):

        try:

            RenkoState(brick_size=size)

        except ValueError:

            continue

        raise AssertionError(
            "Tamanho Renko inválido deveria ser rejeitado."
        )


if __name__ == "__main__":

    tests = (
        teste_normal_permanece_padrao_temporal,
        teste_renko_e_mercado_principal_configuravel,
        teste_renko_fecha_varios_tijolos_no_mesmo_tick,
        teste_contexto_temporal_continua_disponivel_no_renko,
        teste_configuracoes_invalidas_sao_rejeitadas,
    )

    for test in tests:

        test()

    print("OK - Chart Mode NORMAL/RENKO RC3.7")
