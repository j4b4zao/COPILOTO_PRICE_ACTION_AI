"""Testes offline da fundação de Order Flow RC4.0."""

from datetime import datetime, timedelta

from analysis.analysis_pipeline import AnalysisPipeline
from analysis.order_flow import OrderFlow
from connectors.profit_reader import ProfitReader
from core.analysis_context import AnalysisContext
from core.event_bus import EventBus
from core.event_types import EventType
from core.order_flow_state import OrderFlowState
from market_data.collector import Collector
from models.result_base import ResultStatus


class FakeExcel:

    def __init__(self, cells=None):
        self.cells = dict(cells or {})
        for column, header in zip(
            ProfitReader.HEADER_COLUMNS,
            ProfitReader.EXPECTED_HEADERS,
        ):
            self.cells.setdefault(f"{column}1", header)
        self.connected = False

    def conectar(self, path):
        self.connected = bool(path)
        return self.connected

    def ler_celula(self, sheet, cell):
        assert sheet == "Planilha1"
        return self.cells.get(cell)


class FakeReader:

    def __init__(self, readings):
        self.readings = list(readings)

    def obter_dados(self):
        if not self.readings:
            return None
        return self.readings.pop(0)


class FakeClock:

    def __init__(self, amount):
        start = datetime(2026, 8, 21, 10, 0)
        self.timestamps = [
            start + timedelta(seconds=index)
            for index in range(amount)
        ]

    def now(self):
        return self.timestamps.pop(0)


def reading(buy=None, sell=None):
    return {
        "ativo": "WINV26",
        "close": 100.0,
        "volume": 1000.0,
        "agressao_compra": buy,
        "agressao_venda": sell,
    }


def teste_estado_calcula_delta_sem_inventar_primeira_leitura():
    state = OrderFlowState()

    assert state.update(1000.0, 900.0) is False
    assert state.available is True
    assert state.ready is False

    assert state.update(1120.0, 950.0) is True
    assert state.buy_aggression == 120.0
    assert state.sell_aggression == 50.0
    assert state.delta == 70.0
    assert state.total_aggression == 170.0


def teste_estado_reinicia_base_quando_contador_recua():
    state = OrderFlowState()
    state.update(1000.0, 900.0)
    state.update(1100.0, 950.0)

    assert state.update(10.0, 5.0) is False
    assert state.ready is False
    assert state.delta == 0.0

    assert state.update(30.0, 25.0) is True
    assert state.delta == 0.0
    assert state.total_aggression == 40.0


def teste_engine_classifica_compra_venda_e_equilibrio():
    cases = (
        ((100.0, 20.0), "BUY"),
        ((20.0, 100.0), "SELL"),
        ((100.0, 95.0), "BALANCED"),
    )

    for (buy, sell), expected in cases:
        state = OrderFlowState(
            buy_aggression=buy,
            sell_aggression=sell,
            delta=buy - sell,
            total_aggression=buy + sell,
            ready=True,
            available=True,
        )
        context = AnalysisContext(order_flow_state=state)

        OrderFlow().executar(context)

        assert context.order_flow.status == ResultStatus.SUCCESS
        assert context.order_flow.valid is True
        assert context.order_flow.pressure == expected


def teste_engine_explicita_dado_ausente():
    context = AnalysisContext()

    OrderFlow().executar(context)

    assert context.order_flow.status == ResultStatus.SKIPPED
    assert context.order_flow.valid is False
    assert context.order_flow.pressure == "INSUFFICIENT_DATA"
    assert "ORDER_FLOW_DATA_UNAVAILABLE" in context.order_flow.reasons


def teste_collector_integra_agressoes_opcionais():
    collector = Collector(
        excel=FakeExcel(),
        reader=FakeReader((
            reading(1000.0, 900.0),
            reading(1120.0, 950.0),
        )),
        clock=FakeClock(2),
    )

    first = collector.get_data()
    second = collector.get_data()

    assert first.order_flow_state is collector.order_flow
    assert second.order_flow_state is collector.order_flow
    assert second.order_flow_state.ready is True
    assert second.order_flow_state.delta == 70.0


def teste_collector_preserva_operacao_sem_colunas_opcionais():
    collector = Collector(
        excel=FakeExcel(),
        reader=FakeReader((reading(),)),
        clock=FakeClock(1),
    )

    context = collector.get_data()

    assert context is not None
    assert context.order_flow_state.available is False


def teste_profit_reader_mapeia_colunas_o_e_p():
    reader = ProfitReader(FakeExcel({"O2": "1.250", "P2": "980"}))

    data = reader.obter_dados()

    assert data["agressao_compra"] == "1.250"
    assert data["agressao_venda"] == "980"


def teste_pipeline_publica_evento_sem_usar_order_flow_no_score():
    state = OrderFlowState()
    state.update(1000.0, 900.0)
    state.update(1120.0, 950.0)
    context = AnalysisContext(order_flow_state=state)
    bus = EventBus()
    events = []
    bus.subscribe(EventType.ORDER_FLOW_UPDATED, events.append)

    score_before = context.score.total
    AnalysisPipeline(event_bus=bus).executar(context)

    assert len(events) == 1
    assert events[0].data is context
    assert context.order_flow.pressure == "BUY"
    assert context.score.total == score_before


if __name__ == "__main__":
    tests = (
        teste_estado_calcula_delta_sem_inventar_primeira_leitura,
        teste_estado_reinicia_base_quando_contador_recua,
        teste_engine_classifica_compra_venda_e_equilibrio,
        teste_engine_explicita_dado_ausente,
        teste_collector_integra_agressoes_opcionais,
        teste_collector_preserva_operacao_sem_colunas_opcionais,
        teste_profit_reader_mapeia_colunas_o_e_p,
        teste_pipeline_publica_evento_sem_usar_order_flow_no_score,
    )

    for test in tests:
        test()

    print("OK - Order Flow foundation RC4.0")
