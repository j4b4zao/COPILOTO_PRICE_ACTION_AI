"""
tests/test_context_engine_external.py

Teste de integração:

    ContextEngine + ExternalMarketState

RC2.3

Objetivo:

    Verificar que o contexto externo consegue confirmar,
    conflitar ou permanecer neutro em relação ao contexto
    direcional interno.

Este teste NÃO calcula Score.
Este teste NÃO executa Strategy.
Este teste NÃO executa Risk.
Este teste NÃO executa Decision.
"""

from core.analysis_context import AnalysisContext
from brain.context_engine import ContextEngine
from enums.trend import Trend


# ==============================================================
# PREPARAR CONTEXTO INTERNO
# ==============================================================

def preparar_contexto(context, trend):

    # ----------------------------------------------------------
    # STRUCTURE
    # ----------------------------------------------------------

    context.structure.valid = True
    context.structure.trend = trend

    # ----------------------------------------------------------
    # LIQUIDITY
    # ----------------------------------------------------------

    context.liquidity.valid = True

    # ----------------------------------------------------------
    # VOLUME
    # ----------------------------------------------------------

    context.volume.valid = True
    context.volume.high = True
    context.volume.medium = False

    # ----------------------------------------------------------
    # PRICE ACTION
    # ----------------------------------------------------------

    context.price_action.valid = True


# ==============================================================
# PREPARAR CONTEXTO EXTERNO
# ==============================================================

def preparar_externo(
    context,
    risk_on_off,
    global_bias,
    confidence=0.85,
):

    external = context.external_market

    external.valid = True

    external.risk_on_off = risk_on_off

    external.global_bias = global_bias

    external.confidence = confidence


# ==============================================================
# EXECUTAR ENGINE
# ==============================================================

def executar_contexto(
    trend,
    risk_on_off,
    global_bias,
):

    context = AnalysisContext()

    preparar_contexto(
        context,
        trend,
    )

    preparar_externo(
        context,
        risk_on_off,
        global_bias,
    )

    ContextEngine().executar(context)

    return context


# ==============================================================
# TESTE: BUY + RISK ON
# ==============================================================

def teste_buy_confirmado():

    context = executar_contexto(
        Trend.UP,
        "RISK_ON",
        "BULLISH",
    )

    assert context.context.bias == "BUY"

    assert (
        "Contexto externo confirma direção."
        in context.narrative.strengths
    )


# ==============================================================
# TESTE: BUY + RISK OFF
# ==============================================================

def teste_buy_conflito():

    context = executar_contexto(
        Trend.UP,
        "RISK_OFF",
        "BEARISH",
    )

    assert context.context.bias == "BUY"

    assert (
        "Contexto externo conflita com direção."
        in context.narrative.weaknesses
    )


# ==============================================================
# TESTE: SELL + RISK OFF
# ==============================================================

def teste_sell_confirmado():

    context = executar_contexto(
        Trend.DOWN,
        "RISK_OFF",
        "BEARISH",
    )

    assert context.context.bias == "SELL"

    assert (
        "Contexto externo confirma direção."
        in context.narrative.strengths
    )


# ==============================================================
# TESTE: SELL + RISK ON
# ==============================================================

def teste_sell_conflito():

    context = executar_contexto(
        Trend.DOWN,
        "RISK_ON",
        "BULLISH",
    )

    assert context.context.bias == "SELL"

    assert (
        "Contexto externo conflita com direção."
        in context.narrative.weaknesses
    )


# ==============================================================
# TESTE: EXTERNO NEUTRO
# ==============================================================

def teste_externo_neutro():

    context = executar_contexto(
        Trend.UP,
        "NEUTRAL",
        "NEUTRAL",
    )

    assert context.context.bias == "BUY"

    assert (
        "Contexto externo neutro."
        in context.narrative.weaknesses
    )


# ==============================================================
# EXECUÇÃO
# ==============================================================

def main():

    print()
    print("=" * 72)
    print("TESTE CONTEXT ENGINE + EXTERNAL MARKET RC2.3")
    print("=" * 72)

    erros = []

    testes = [
        (
            "BUY + RISK_ON",
            teste_buy_confirmado,
        ),
        (
            "BUY + RISK_OFF",
            teste_buy_conflito,
        ),
        (
            "SELL + RISK_OFF",
            teste_sell_confirmado,
        ),
        (
            "SELL + RISK_ON",
            teste_sell_conflito,
        ),
        (
            "EXTERNAL NEUTRAL",
            teste_externo_neutro,
        ),
    ]

    for nome, teste in testes:

        print()
        print("TESTE:", nome)
        print("-" * 72)

        try:

            teste()

            print("OK")

        except AssertionError as erro:

            erros.append(
                f"{nome}: {erro}"
            )

            print("FALHOU")

        except Exception as erro:

            erros.append(
                f"{nome}: "
                f"{type(erro).__name__}: {erro}"
            )

            print("ERRO")

    print()
    print("=" * 72)

    if erros:

        print("⚠️ TESTE PRECISA DE CORREÇÃO")

        print()

        for erro in erros:

            print("-", erro)

        print()

        print(
            "O teste foi criado corretamente, "
            "mas o ContextEngine ainda não possui "
            "a integração externa."
        )

        return

    print(
        "🏆 CONTEXT ENGINE + EXTERNAL CONTEXT "
        "RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()