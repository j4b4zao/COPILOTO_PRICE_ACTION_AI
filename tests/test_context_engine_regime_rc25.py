"""
Testes controlados da integração contextual do Market Regime.

O regime pode confirmar, conflitar ou indicar lateralidade,
mas não altera score, confluências, checklist ou validade.
"""

from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from enums.trend import Trend


def preparar_contexto(
    structure_trend,
    regime_trend=None,
):

    context = AnalysisContext()

    context.structure.valid = True
    context.structure.trend = structure_trend

    context.liquidity.valid = True

    context.volume.valid = True
    context.volume.high = True

    context.price_action.valid = True

    if regime_trend is not None:

        context.regime.valid = True
        context.regime.trend = regime_trend

        if regime_trend == Trend.UP:

            context.regime.regime = "TREND_UP"

        elif regime_trend == Trend.DOWN:

            context.regime.regime = "TREND_DOWN"

        elif regime_trend == Trend.SIDEWAYS:

            context.regime.regime = "RANGE"

    ContextEngine().executar(context)

    return context


def snapshot_operacional(context):

    return {
        "valid": context.context.valid,
        "bias": context.context.bias,
        "market_state": context.context.market_state,
        "score": context.context.score,
        "confluences": context.context.confluences,
        "checklist_ready": context.checklist.ready,
        "checklist_score": context.checklist.score,
    }


def teste_buy_confirmado():

    context = preparar_contexto(
        Trend.UP,
        Trend.UP,
    )

    assert context.context.bias == "BUY"

    assert (
        "Regime de mercado confirma direção."
        in context.narrative.strengths
    )


def teste_buy_em_conflito():

    context = preparar_contexto(
        Trend.UP,
        Trend.DOWN,
    )

    assert context.context.bias == "BUY"

    assert (
        "Regime de mercado conflita com direção."
        in context.narrative.weaknesses
    )


def teste_sell_confirmado():

    context = preparar_contexto(
        Trend.DOWN,
        Trend.DOWN,
    )

    assert context.context.bias == "SELL"

    assert (
        "Regime de mercado confirma direção."
        in context.narrative.strengths
    )


def teste_sell_em_conflito():

    context = preparar_contexto(
        Trend.DOWN,
        Trend.UP,
    )

    assert context.context.bias == "SELL"

    assert (
        "Regime de mercado conflita com direção."
        in context.narrative.weaknesses
    )


def teste_regime_lateral():

    context = preparar_contexto(
        Trend.UP,
        Trend.SIDEWAYS,
    )

    assert context.context.bias == "BUY"

    assert (
        "Regime de mercado lateral."
        in context.narrative.weaknesses
    )


def teste_regime_invalido_ignorado():

    context = preparar_contexto(
        Trend.UP,
    )

    messages = (
        context.narrative.strengths
        + context.narrative.weaknesses
    )

    assert all(
        not message.startswith(
            "Regime de mercado"
        )
        for message in messages
    )


def teste_sem_impacto_operacional():

    without_regime = preparar_contexto(
        Trend.UP,
    )

    confirming_regime = preparar_contexto(
        Trend.UP,
        Trend.UP,
    )

    conflicting_regime = preparar_contexto(
        Trend.UP,
        Trend.DOWN,
    )

    baseline = snapshot_operacional(
        without_regime
    )

    assert snapshot_operacional(
        confirming_regime
    ) == baseline

    assert snapshot_operacional(
        conflicting_regime
    ) == baseline

    assert baseline == {
        "valid": True,
        "bias": "BUY",
        "market_state": "FAVORABLE",
        "score": 0.0,
        "confluences": 5,
        "checklist_ready": True,
        "checklist_score": 6,
    }


def main():

    print()
    print("=" * 72)
    print("TESTE CONTEXT ENGINE + MARKET REGIME RC2.5")
    print("=" * 72)

    tests = [
        teste_buy_confirmado,
        teste_buy_em_conflito,
        teste_sell_confirmado,
        teste_sell_em_conflito,
        teste_regime_lateral,
        teste_regime_invalido_ignorado,
        teste_sem_impacto_operacional,
    ]

    for test in tests:

        test()

        print(
            f"✅ {test.__name__}"
        )

    print()
    print("🏆 CONTEXT ENGINE + MARKET REGIME RC2.5 APROVADO")


if __name__ == "__main__":

    main()
