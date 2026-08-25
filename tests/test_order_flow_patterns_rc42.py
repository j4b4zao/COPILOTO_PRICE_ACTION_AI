"""Testes offline de divergência, absorção e exaustão RC4.2."""

from analysis.order_flow import OrderFlow
from core.analysis_context import AnalysisContext
from core.order_flow_state import OrderFlowState
from monitor.order_flow_monitor import OrderFlowMonitor


def build_state(samples):
    state = OrderFlowState()
    cumulative_buy = 1000.0
    cumulative_sell = 1000.0
    first_price = samples[0][2] - samples[0][3]
    state.update(cumulative_buy, cumulative_sell, price=first_price)

    for buy, sell, price, _ in samples:
        cumulative_buy += buy
        cumulative_sell += sell
        state.update(cumulative_buy, cumulative_sell, price=price)

    return state


def sample(buy, sell, price, previous_price):
    return buy, sell, price, price - previous_price


def analyze(samples):
    state = build_state(samples)
    context = AnalysisContext(order_flow_state=state)
    OrderFlow().executar(context)
    return state, context.order_flow


def teste_historico_minimo_bloqueia_padrao_sem_bloquear_delta():
    samples = (
        sample(100.0, 50.0, 101.0, 100.0),
        sample(100.0, 50.0, 102.0, 101.0),
        sample(100.0, 50.0, 103.0, 102.0),
    )

    state, result = analyze(samples)

    assert state.sample_count == 3
    assert result.valid is True
    assert result.patterns_ready is False
    assert result.divergence == "INSUFFICIENT_DATA"
    assert "ORDER_FLOW_PATTERN_HISTORY_PENDING" in result.reasons


def teste_preco_sobe_com_delta_vendedor_indica_divergencia_e_absorcao():
    prices = (101.0, 102.0, 103.0, 104.0, 105.0, 106.0)
    samples = tuple(
        sample(20.0, 100.0, price, price - 1.0)
        for price in prices
    )

    _, result = analyze(samples)

    assert result.patterns_ready is True
    assert result.recent_price_change == 5.0
    assert result.recent_delta == -400.0
    assert result.divergence == "PRICE_UP_DELTA_DOWN"
    assert result.absorption == "BUY_ABSORPTION"
    assert result.exhaustion == "NONE"


def teste_preco_cai_com_delta_comprador_indica_divergencia_e_absorcao():
    prices = (99.0, 98.0, 97.0, 96.0, 95.0, 94.0)
    samples = tuple(
        sample(100.0, 20.0, price, price + 1.0)
        for price in prices
    )

    _, result = analyze(samples)

    assert result.recent_price_change == -5.0
    assert result.recent_delta == 400.0
    assert result.divergence == "PRICE_DOWN_DELTA_UP"
    assert result.absorption == "SELL_ABSORPTION"


def teste_queda_de_atividade_identifica_exaustao_compradora():
    samples = (
        sample(400.0, 100.0, 101.0, 100.0),
        sample(400.0, 100.0, 102.0, 101.0),
        sample(400.0, 100.0, 103.0, 102.0),
        sample(80.0, 20.0, 104.0, 103.0),
        sample(80.0, 20.0, 105.0, 104.0),
        sample(80.0, 20.0, 106.0, 105.0),
    )

    _, result = analyze(samples)

    assert result.aggression_activity_ratio == 0.20
    assert result.exhaustion == "BUY_EXHAUSTION"


def teste_queda_de_atividade_identifica_exaustao_vendedora():
    samples = (
        sample(100.0, 400.0, 99.0, 100.0),
        sample(100.0, 400.0, 98.0, 99.0),
        sample(100.0, 400.0, 97.0, 98.0),
        sample(20.0, 80.0, 96.0, 97.0),
        sample(20.0, 80.0, 95.0, 96.0),
        sample(20.0, 80.0, 94.0, 95.0),
    )

    _, result = analyze(samples)

    assert result.aggression_activity_ratio == 0.20
    assert result.exhaustion == "SELL_EXHAUSTION"


def teste_reset_preserva_nova_base_de_preco():
    samples = tuple(
        sample(100.0, 50.0, 101.0 + index, 100.0 + index)
        for index in range(6)
    )
    state = build_state(samples)

    state.update(10.0, 10.0, price=200.0)

    assert state.sample_count == 0
    assert tuple(state.price_history) == (200.0,)

    state.update(20.0, 15.0, price=201.0)

    assert tuple(state.price_history) == (200.0, 201.0)


def teste_monitor_exibe_padrao_sem_impacto_operacional():
    samples = tuple(
        sample(20.0, 100.0, 101.0 + index, 100.0 + index)
        for index in range(6)
    )
    _, result = analyze(samples)
    context = AnalysisContext()
    context.order_flow = result

    output = OrderFlowMonitor.render(context)

    assert "Padrões prontos: True" in output
    assert "Divergência....: PRICE_UP_DELTA_DOWN" in output
    assert "Absorção.......: BUY_ABSORPTION" in output
    assert "Impacto.........: somente informativo" in output


if __name__ == "__main__":
    tests = (
        teste_historico_minimo_bloqueia_padrao_sem_bloquear_delta,
        teste_preco_sobe_com_delta_vendedor_indica_divergencia_e_absorcao,
        teste_preco_cai_com_delta_comprador_indica_divergencia_e_absorcao,
        teste_queda_de_atividade_identifica_exaustao_compradora,
        teste_queda_de_atividade_identifica_exaustao_vendedora,
        teste_reset_preserva_nova_base_de_preco,
        teste_monitor_exibe_padrao_sem_impacto_operacional,
    )

    for test in tests:
        test()

    print("OK - Order Flow patterns RC4.2")
