"""Testes offline da integração experimental Order Flow -> Score RC4.5."""

from ai.score_engine import ScoreEngine
from config.settings import ENABLE_ORDER_FLOW_SCORE
from core.analysis_context import AnalysisContext


def context_with_strategy(signal="BUY", strategy_score=80.0):
    context = AnalysisContext()
    context.strategy.valid = True
    context.strategy.signal = signal
    context.strategy.score = strategy_score
    return context


def confirmed_order_flow(
    context,
    *,
    divergence="PRICE_UP_DELTA_DOWN",
    absorption="BUY_ABSORPTION",
    exhaustion="NONE",
    confidence=0.80,
):
    result = context.order_flow
    result.valid = True
    result.patterns_ready = True
    result.pattern_confirmed = True
    result.pattern_quality = "HIGH"
    result.pattern_confidence = confidence
    result.divergence = divergence
    result.absorption = absorption
    result.exhaustion = exhaustion


def teste_experimento_desativado_por_padrao():
    assert ENABLE_ORDER_FLOW_SCORE is False

    context = context_with_strategy()
    confirmed_order_flow(context)

    ScoreEngine().executar(context)

    assert context.score.total == 8.0
    assert context.score.breakdown == {"Strategy": 8.0}
    assert context.score.order_flow_experiment_enabled is False
    assert context.score.order_flow_applied is False


def teste_desligado_preserva_resultado_bit_a_bit():
    first = context_with_strategy()
    second = context_with_strategy()
    confirmed_order_flow(first)
    confirmed_order_flow(second)

    ScoreEngine().executar(first)
    ScoreEngine(enable_order_flow=False).executar(second)

    assert first.score.total == second.score.total
    assert first.score.breakdown == second.score.breakdown
    assert first.score.grade == second.score.grade
    assert first.score.valid == second.score.valid


def teste_padrao_confirmado_alinhado_aplica_bonus_limitado():
    context = context_with_strategy(signal="BUY")
    confirmed_order_flow(context, confidence=0.80)

    ScoreEngine(
        enable_order_flow=True,
        order_flow_weight=5.0,
    ).executar(context)

    assert context.score.breakdown["Strategy"] == 8.0
    assert context.score.breakdown["OrderFlow"] == 4.0
    assert context.score.total == 12.0
    assert context.score.order_flow_experiment_enabled is True
    assert context.score.order_flow_applied is True
    assert context.score.order_flow_direction == "BUY"
    assert context.score.order_flow_contribution == 4.0


def teste_padrao_contrario_nao_altera_score():
    context = context_with_strategy(signal="SELL")
    confirmed_order_flow(context, confidence=1.0)

    ScoreEngine(enable_order_flow=True).executar(context)

    assert context.score.total == 8.0
    assert "OrderFlow" not in context.score.breakdown
    assert context.score.order_flow_direction == "BUY"
    assert context.score.order_flow_applied is False


def teste_padrao_nao_confirmado_nao_altera_score():
    context = context_with_strategy()
    confirmed_order_flow(context)
    context.order_flow.pattern_confirmed = False

    ScoreEngine(enable_order_flow=True).executar(context)

    assert context.score.total == 8.0
    assert "OrderFlow" not in context.score.breakdown
    assert context.score.order_flow_applied is False


def teste_padroes_direcionalmente_conflitantes_sao_bloqueados():
    context = context_with_strategy()
    confirmed_order_flow(
        context,
        divergence="PRICE_UP_DELTA_DOWN",
        absorption="BUY_ABSORPTION",
        exhaustion="BUY_EXHAUSTION",
        confidence=1.0,
    )

    ScoreEngine(enable_order_flow=True).executar(context)

    assert context.score.order_flow_direction == "NONE"
    assert context.score.order_flow_applied is False
    assert "OrderFlow" not in context.score.breakdown


def teste_bonus_sell_alinhado_e_suportado():
    context = context_with_strategy(signal="SELL")
    confirmed_order_flow(
        context,
        divergence="PRICE_DOWN_DELTA_UP",
        absorption="SELL_ABSORPTION",
        confidence=0.60,
    )

    ScoreEngine(enable_order_flow=True).executar(context)

    assert context.score.order_flow_direction == "SELL"
    assert context.score.order_flow_contribution == 3.0
    assert context.score.breakdown["OrderFlow"] == 3.0


def teste_peso_experimental_invalido_e_rejeitado():
    for weight in (-1.0, 10.1, float("inf"), "INVALID"):
        try:
            ScoreEngine(
                enable_order_flow=True,
                order_flow_weight=weight,
            )
        except ValueError:
            continue

        raise AssertionError("Peso inválido deveria ser rejeitado.")


if __name__ == "__main__":
    tests = (
        teste_experimento_desativado_por_padrao,
        teste_desligado_preserva_resultado_bit_a_bit,
        teste_padrao_confirmado_alinhado_aplica_bonus_limitado,
        teste_padrao_contrario_nao_altera_score,
        teste_padrao_nao_confirmado_nao_altera_score,
        teste_padroes_direcionalmente_conflitantes_sao_bloqueados,
        teste_bonus_sell_alinhado_e_suportado,
        teste_peso_experimental_invalido_e_rejeitado,
    )

    for test in tests:
        test()

    print("OK - Order Flow Score experiment RC4.5")
