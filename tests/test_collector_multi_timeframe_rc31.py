"""
Testes controlados da integração Collector RC11 com
MultiTimeframeState RC3.0.

Não utiliza Excel, DDE, rede ou relógio real.
"""

from datetime import datetime

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from core.multi_timeframe_state import MultiTimeframeState
from market_data.collector import Collector


class FakeExcel:

    def __init__(self, connected=True):

        self.connected = connected
        self.connected_path = None

    def conectar(self, path):

        self.connected_path = path

        return self.connected


class FakeReader:

    def __init__(self, readings):

        self.readings = list(readings)
        self.index = 0

    def obter_dados(self):

        if self.index >= len(self.readings):

            return None

        reading = self.readings[
            self.index
        ]

        self.index += 1

        return reading


class FakeClock:

    def __init__(self, timestamps):

        self.timestamps = list(timestamps)
        self.index = 0

    def now(self):

        timestamp = self.timestamps[
            self.index
        ]

        self.index += 1

        return timestamp


def timestamp(minute):

    return datetime(
        2026,
        8,
        20,
        10,
        minute,
    )


def reading(
    price,
    volume,
    symbol="WINV26",
):

    return {
        "ativo": symbol,
        "close": price,
        "open": price,
        "high": price,
        "low": price,
        "volume": volume,
    }


def create_collector(
    readings,
    timestamps,
    state=None,
):

    excel = FakeExcel()

    collector = Collector(
        excel=excel,
        reader=FakeReader(readings),
        multi_timeframe=state,
        clock=FakeClock(timestamps),
    )

    assert excel.connected_path is not None

    return collector


def teste_collector_alimenta_fronteiras_independentes():

    collector = create_collector(
        readings=[
            reading(100.0, 1000.0),
            reading(101.0, 1100.0),
            reading(102.0, 1200.0),
            reading(103.0, 1300.0),
        ],
        timestamps=[
            timestamp(0),
            timestamp(1),
            timestamp(5),
            timestamp(15),
        ],
    )

    contexts = [
        collector.get_data()
        for _ in range(4)
    ]

    state = collector.multi_timeframe

    assert all(
        isinstance(context, AnalysisContext)
        for context in contexts
    )

    assert all(
        context.multi_timeframe is state
        for context in contexts
    )

    assert all(
        context.market is state.primary
        for context in contexts
    )

    assert state.get("M1").candle_count == 4
    assert state.get("M5").candle_count == 3
    assert state.get("M15").candle_count == 2

    assert collector.last_new_candles == {
        "M1": True,
        "M5": True,
        "M15": True,
    }


def teste_collector_preserva_ohlc_e_volume_por_timeframe():

    collector = create_collector(
        readings=[
            reading(100.0, 1000.0),
            reading(105.0, 1100.0),
            reading(95.0, 1200.0),
        ],
        timestamps=[
            timestamp(0),
            timestamp(1),
            timestamp(2),
        ],
    )

    context = None

    for _ in range(3):

        context = collector.get_data()

    m1 = context.multi_timeframe.get("M1")
    m5 = context.multi_timeframe.get("M5")
    m15 = context.multi_timeframe.get("M15")

    assert context.market is m1
    assert context.market.timeframe == "M1"

    assert m1.candle_count == 3
    assert m5.candle_count == 1
    assert m15.candle_count == 1

    assert m1.last_candle.open == 95.0
    assert m1.last_candle.close == 95.0
    assert m1.last_candle.volume == 100.0

    assert m5.last_candle.open == 100.0
    assert m5.last_candle.high == 105.0
    assert m5.last_candle.low == 95.0
    assert m5.last_candle.close == 95.0
    assert m5.last_candle.volume == 200.0

    assert m15.last_candle.open == 100.0
    assert m15.last_candle.high == 105.0
    assert m15.last_candle.low == 95.0
    assert m15.last_candle.close == 95.0
    assert m15.last_candle.volume == 200.0


def teste_collector_reutiliza_estado_injetado():

    state = MultiTimeframeState()

    collector = create_collector(
        readings=[
            reading(100.0, 1000.0),
        ],
        timestamps=[
            timestamp(0),
        ],
        state=state,
    )

    context = collector.get_data()

    assert collector.multi_timeframe is state
    assert collector.market is state.primary
    assert context.multi_timeframe is state
    assert context.market is state.primary


def teste_collector_rejeita_identificacao_e_preco_invalidos():

    collector = create_collector(
        readings=[
            reading(100.0, 1000.0, symbol=""),
            reading(0.0, 1000.0),
            reading(100.0, -10.0),
        ],
        timestamps=[
            timestamp(2),
        ],
    )

    assert collector.get_data() is None
    assert collector.get_data() is None

    context = collector.get_data()

    assert context is not None
    assert context.market.candle_count == 1
    assert context.market.volume == 0.0
    assert context.market.last_candle.volume == 0.0


def teste_collector_sem_leitura_nao_altera_estado():

    collector = create_collector(
        readings=[],
        timestamps=[],
    )

    assert collector.get_data() is None
    assert collector.market.candle_count == 0
    assert collector.multi_timeframe.get("M5").candle_count == 0
    assert collector.multi_timeframe.get("M15").candle_count == 0


def teste_contexto_do_collector_e_aceito_pelo_pipeline():

    collector = create_collector(
        readings=[
            reading(100.0 + minute, 1000.0 + minute * 100.0)
            for minute in range(6)
        ],
        timestamps=[
            timestamp(minute)
            for minute in range(6)
        ],
    )

    context = None

    for _ in range(6):

        context = collector.get_data()

    result = AnalysisPipeline().executar(
        context
    )

    assert result is context
    assert result.market is collector.market
    assert result.multi_timeframe is collector.multi_timeframe
    assert result.market.timeframe == "M1"
    assert result.market.candle_count == 6


def teste_conexao_invalida_permanece_bloqueada():

    try:

        Collector(
            excel=FakeExcel(connected=False),
            reader=FakeReader([]),
            clock=FakeClock([]),
        )

    except RuntimeError:

        return

    raise AssertionError(
        "Collector deveria rejeitar conexão inválida."
    )


def main():

    print()
    print("=" * 72)
    print("TESTE COLLECTOR MULTI-TIMEFRAME RC3.1")
    print("=" * 72)

    tests = [
        teste_collector_alimenta_fronteiras_independentes,
        teste_collector_preserva_ohlc_e_volume_por_timeframe,
        teste_collector_reutiliza_estado_injetado,
        teste_collector_rejeita_identificacao_e_preco_invalidos,
        teste_collector_sem_leitura_nao_altera_estado,
        teste_contexto_do_collector_e_aceito_pelo_pipeline,
        teste_conexao_invalida_permanece_bloqueada,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 COLLECTOR MULTI-TIMEFRAME RC3.1 APROVADO")


if __name__ == "__main__":

    main()
