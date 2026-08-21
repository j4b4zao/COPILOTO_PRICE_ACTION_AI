"""Testes offline da confiança de padrões de Order Flow RC4.4."""

from analysis.order_flow import OrderFlow
from core.analysis_context import AnalysisContext
from core.order_flow_state import OrderFlowState
from monitor.order_flow_monitor import OrderFlowMonitor


def analyze(prices, buy_step, sell_step):
    state = OrderFlowState()
    cumulative_buy = 1000.0
    cumulative_sell = 1000.0
    state.update(cumulative_buy, cumulative_sell, price=prices[0])

    for price in prices[1:]:
        cumulative_buy += buy_step
        cumulative_sell += sell_step
        state.update(cumulative_buy, cumulative_sell, price=price)

    context = AnalysisContext(order_flow_state=state)
    OrderFlow().executar(context)
    return state, context


def teste_padrao_medio_e_confirmado_com_seis_amostras_consistentes():
    prices = tuple(100.0 + index for index in range(7))
    state, context = analyze(prices, buy_step=20.0, sell_step=100.0)
    result = context.order_flow

    assert state.recent_delta_dominance == 2.0 / 3.0
    assert state.recent_price_efficiency == 1.0
    assert result.history_maturity == 0.30
    assert 0.69 < result.pattern_confidence < 0.70
    assert result.pattern_quality == "MEDIUM"
    assert result.pattern_confirmed is True
    assert "ORDER_FLOW_PATTERN_CONFIRMED" in result.reasons


def teste_padrao_alto_exige_historico_maduro_e_movimento_eficiente():
    prices = tuple(100.0 + index for index in range(21))
    _, context = analyze(prices, buy_step=0.0, sell_step=100.0)
    result = context.order_flow

    assert result.sample_count == 20
    assert result.delta_dominance == 1.0
    assert result.price_efficiency == 1.0
    assert result.history_maturity == 1.0
    assert result.pattern_confidence == 1.0
    assert result.pattern_quality == "HIGH"
    assert result.pattern_confirmed is True


def teste_movimento_instavel_rebaixa_padrao_e_evitar_falso_sinal():
    prices = (100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0)
    _, context = analyze(prices, buy_step=100.0, sell_step=20.0)
    result = context.order_flow

    assert result.divergence == "PRICE_DOWN_DELTA_UP"
    assert result.price_efficiency == 0.20
    assert result.pattern_confidence < 0.50
    assert result.pattern_quality == "LOW"
    assert result.pattern_confirmed is False
    assert "ORDER_FLOW_PATTERN_LOW_CONFIDENCE" in result.reasons


def teste_sem_padrao_nao_recebe_confianca_artificial():
    prices = tuple(100.0 + index for index in range(7))
    _, context = analyze(prices, buy_step=100.0, sell_step=20.0)
    result = context.order_flow

    assert result.divergence == "NONE"
    assert result.absorption == "NONE"
    assert result.exhaustion == "NONE"
    assert result.pattern_confidence == 0.0
    assert result.pattern_quality == "NONE"
    assert result.pattern_confirmed is False


def teste_historico_insuficiente_mantem_confianca_indisponivel():
    prices = (100.0, 101.0, 102.0, 103.0)
    _, context = analyze(prices, buy_step=20.0, sell_step=100.0)
    result = context.order_flow

    assert result.patterns_ready is False
    assert result.pattern_confidence == 0.0
    assert result.pattern_quality == "INSUFFICIENT_DATA"
    assert result.pattern_confirmed is False


def teste_confianca_permanece_fora_do_score_e_decision():
    prices = tuple(100.0 + index for index in range(21))
    state = OrderFlowState()
    cumulative_buy = 1000.0
    cumulative_sell = 1000.0
    state.update(cumulative_buy, cumulative_sell, price=prices[0])

    for price in prices[1:]:
        cumulative_sell += 100.0
        state.update(cumulative_buy, cumulative_sell, price=price)

    context = AnalysisContext(order_flow_state=state)
    score_before = context.score.total
    decision_before = context.decision.action

    OrderFlow().executar(context)

    assert context.order_flow.pattern_confirmed is True
    assert context.score.total == score_before
    assert context.decision.action == decision_before


def teste_monitor_exibe_componentes_da_confianca():
    prices = tuple(100.0 + index for index in range(7))
    _, context = analyze(prices, buy_step=20.0, sell_step=100.0)

    output = OrderFlowMonitor.render(context)

    assert "Dominância Delta: 0.67" in output
    assert "Eficiência preço: 1.00" in output
    assert "Maturidade hist.: 0.30" in output
    assert "Qualidade.......: MEDIUM" in output
    assert "Confirmado......: True" in output
    assert "Impacto.........: somente informativo" in output


if __name__ == "__main__":
    tests = (
        teste_padrao_medio_e_confirmado_com_seis_amostras_consistentes,
        teste_padrao_alto_exige_historico_maduro_e_movimento_eficiente,
        teste_movimento_instavel_rebaixa_padrao_e_evitar_falso_sinal,
        teste_sem_padrao_nao_recebe_confianca_artificial,
        teste_historico_insuficiente_mantem_confianca_indisponivel,
        teste_confianca_permanece_fora_do_score_e_decision,
        teste_monitor_exibe_componentes_da_confianca,
    )

    for test in tests:
        test()

    print("OK - Order Flow confidence RC4.4")
