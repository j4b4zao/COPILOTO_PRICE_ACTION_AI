"""
tests/test_external_context_engine.py

Teste controlado do ExternalContextEngine.

Cenários:

1. RISK_ON
2. RISK_OFF
3. NEUTRAL

Não utiliza dados reais.
"""

from external_context.external_market_state import (
    ExternalMarketState,
)

from external_context.external_context_engine import (
    ExternalContextEngine,
)


# ==============================================================
# RISK ON
# ==============================================================

def preparar_risk_on():

    state = ExternalMarketState()

    state.valid = True

    state.us500 = 6400.0
    state.nasdaq = 23700.0
    state.dxy = 98.5
    state.vix = 15.0

    state.us500_change = 0.80
    state.nasdaq_change = 1.10
    state.dxy_change = -0.30
    state.vix_change = -4.00

    return state


# ==============================================================
# RISK OFF
# ==============================================================

def preparar_risk_off():

    state = ExternalMarketState()

    state.valid = True

    state.us500 = 6250.0
    state.nasdaq = 23100.0
    state.dxy = 100.0
    state.vix = 21.0

    state.us500_change = -1.20
    state.nasdaq_change = -1.50
    state.dxy_change = 0.70
    state.vix_change = 8.00

    return state


# ==============================================================
# NEUTRAL
# ==============================================================

def preparar_neutral():

    state = ExternalMarketState()

    state.valid = True

    state.us500 = 6350.0
    state.nasdaq = 23500.0
    state.dxy = 99.0
    state.vix = 17.0

    # Apenas dois fatores positivos e dois negativos.
    state.us500_change = 0.50
    state.nasdaq_change = -0.40
    state.dxy_change = 0.20
    state.vix_change = -2.00

    return state


# ==============================================================
# EXECUTAR
# ==============================================================

def executar_teste(
    nome,
    preparador,
    esperado_risk,
    esperado_bias,
):

    print()
    print("=" * 72)
    print(
        f"TESTE EXTERNAL CONTEXT: {nome}"
    )
    print("=" * 72)

    state = preparador()

    ExternalContextEngine().executar(
        state
    )

    print()
    print("RESULTADO")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    print(
        f"risk_on_off  : "
        f"{state.risk_on_off}"
    )

    print(
        f"global_bias  : "
        f"{state.global_bias}"
    )

    print(
        f"confidence   : "
        f"{state.confidence:.3f}"
    )

    print()
    print("REASONS")
    print("-" * 72)

    for reason in state.reasons:

        print(
            f"- {reason}"
        )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    erros = []

    if not state.valid:

        erros.append(
            "Estado deveria permanecer válido."
        )

    if state.risk_on_off != esperado_risk:

        erros.append(
            f"Risk esperado: "
            f"{esperado_risk}; "
            f"obtido: "
            f"{state.risk_on_off}"
        )

    if state.global_bias != esperado_bias:

        erros.append(
            f"Bias esperado: "
            f"{esperado_bias}; "
            f"obtido: "
            f"{state.global_bias}"
        )

    if state.confidence < 0:

        erros.append(
            "Confidence não pode ser negativo."
        )

    # ==========================================================
    # RESULTADO
    # ==========================================================

    print()
    print("=" * 72)

    if erros:

        print(
            "❌ RESULTADO: FALHOU"
        )

        print()

        for erro in erros:

            print(
                f" - {erro}"
            )

        return False

    print(
        "✅ RESULTADO: APROVADO"
    )

    return True


# ==============================================================
# MAIN
# ==============================================================

def main():

    risk_on_ok = executar_teste(
        "RISK ON",
        preparar_risk_on,
        "RISK_ON",
        "BULLISH",
    )

    risk_off_ok = executar_teste(
        "RISK OFF",
        preparar_risk_off,
        "RISK_OFF",
        "BEARISH",
    )

    neutral_ok = executar_teste(
        "NEUTRAL",
        preparar_neutral,
        "NEUTRAL",
        "NEUTRAL",
    )

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print(
        f"RISK ON  : "
        f"{'PASSOU' if risk_on_ok else 'FALHOU'}"
    )

    print(
        f"RISK OFF : "
        f"{'PASSOU' if risk_off_ok else 'FALHOU'}"
    )

    print(
        f"NEUTRAL  : "
        f"{'PASSOU' if neutral_ok else 'FALHOU'}"
    )

    print()

    if (
        risk_on_ok
        and risk_off_ok
        and neutral_ok
    ):

        print(
            "🏆 EXTERNAL CONTEXT ENGINE APROVADO"
        )

    else:

        print(
            "⚠️ EXTERNAL CONTEXT ENGINE "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()