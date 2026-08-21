"""Testes offline do histórico e monitor de Order Flow RC4.1."""

from analysis.order_flow import OrderFlow
from core.analysis_context import AnalysisContext
from core.event import Event
from core.order_flow_state import OrderFlowState
from monitor.debug_monitor import DebugMonitor
from monitor.order_flow_monitor import OrderFlowMonitor


def build_state(deltas):
    state = OrderFlowState()
    cumulative_buy = 1000.0
    cumulative_sell = 1000.0
    state.update(cumulative_buy, cumulative_sell)

    for delta in deltas:
        if delta >= 0:
            cumulative_buy += delta
        else:
            cumulative_sell += abs(delta)

        state.update(cumulative_buy, cumulative_sell)

    return state


def teste_historico_delta_acumulado_e_janela_recente():
    state = build_state((10.0, -5.0, 20.0, -2.0, 7.0, 30.0))

    assert tuple(state.history) == (10.0, -5.0, 20.0, -2.0, 7.0, 30.0)
    assert state.cumulative_delta == 60.0
    assert state.recent_delta == 50.0
    assert state.average_delta == 10.0
    assert state.sample_count == 6


def teste_historico_limitado_sem_perder_acumulado_da_sessao():
    state = build_state(tuple(1.0 for _ in range(60)))

    assert state.sample_count == state.HISTORY_SIZE
    assert len(state.history) == 50
    assert state.cumulative_delta == 60.0
    assert state.recent_delta == 5.0


def teste_ausencia_temporaria_preserva_historico_confirmado():
    state = build_state((10.0, 20.0))

    state.mark_unavailable()

    assert state.available is False
    assert state.ready is False
    assert tuple(state.history) == (10.0, 20.0)
    assert state.cumulative_delta == 30.0


def teste_reinicio_de_contador_reinicia_historico_da_sessao():
    state = build_state((10.0, 20.0))

    assert state.update(5.0, 5.0) is False
    assert state.sample_count == 0
    assert state.cumulative_delta == 0.0

    assert state.update(15.0, 10.0) is True
    assert state.delta == 5.0
    assert state.cumulative_delta == 5.0


def teste_engine_publica_metricas_e_tendencia_recente():
    state = build_state((-30.0, 5.0, -20.0))
    context = AnalysisContext(order_flow_state=state)

    OrderFlow().executar(context)

    result = context.order_flow
    assert result.valid is True
    assert result.delta == -20.0
    assert result.recent_delta == -45.0
    assert result.cumulative_delta == -45.0
    assert result.average_delta == -15.0
    assert result.sample_count == 3
    assert result.trend == "SELLING"


def teste_monitor_exibe_diagnostico_informativo_completo():
    context = AnalysisContext(
        order_flow_state=build_state((40.0, -10.0, 20.0))
    )
    OrderFlow().executar(context)

    output = OrderFlowMonitor.render(context)

    assert "[ ORDER FLOW - INFORMATIVO ]" in output
    assert "Delta atual....: +20" in output
    assert "Delta recente..: +50" in output
    assert "Delta acumulado: +50" in output
    assert "Amostras.......: 3" in output
    assert "Tendência......: BUYING" in output
    assert "Impacto.........: somente informativo" in output


def teste_monitor_explicita_dados_indisponiveis():
    context = AnalysisContext()
    OrderFlow().executar(context)

    output = OrderFlowMonitor.render(context)

    assert "Status.........: SKIPPED" in output
    assert "Pressão........: INSUFFICIENT_DATA" in output
    assert "ORDER_FLOW_DATA_UNAVAILABLE" in output


def teste_debug_monitor_consumidor_event_data():
    monitor = object.__new__(DebugMonitor)
    received = []
    monitor.show = received.append
    context = AnalysisContext()

    monitor.on_loop_completed(Event("LOOP_COMPLETED", context))

    assert received == [context]


if __name__ == "__main__":
    tests = (
        teste_historico_delta_acumulado_e_janela_recente,
        teste_historico_limitado_sem_perder_acumulado_da_sessao,
        teste_ausencia_temporaria_preserva_historico_confirmado,
        teste_reinicio_de_contador_reinicia_historico_da_sessao,
        teste_engine_publica_metricas_e_tendencia_recente,
        teste_monitor_exibe_diagnostico_informativo_completo,
        teste_monitor_explicita_dados_indisponiveis,
        teste_debug_monitor_consumidor_event_data,
    )

    for test in tests:
        test()

    print("OK - Order Flow history RC4.1")
