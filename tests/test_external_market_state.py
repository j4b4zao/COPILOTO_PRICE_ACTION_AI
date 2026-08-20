"""
tests/test_external_market_state.py

Teste controlado do ExternalMarketState.

Objetivo:

- validar criação
- validar preenchimento
- validar clear()
- garantir classificação inicial NEUTRAL

Não utiliza dados reais.
"""

from external_context.external_market_state import (
    ExternalMarketState,
)


def executar_teste():

    print()
    print("=" * 72)
    print("TESTE EXTERNAL MARKET STATE")
    print("=" * 72)

    state = ExternalMarketState()

    # ==========================================================
    # ESTADO INICIAL
    # ==========================================================

    print()
    print("ESTADO INICIAL")
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
        f"{state.confidence}"
    )

    # ==========================================================
    # DADOS CONTROLADOS
    # ==========================================================

    state.valid = True

    state.us500 = 6400.0

    state.nasdaq = 23700.0

    state.dxy = 98.5

    state.vix = 15.0

    state.us10y = 4.25

    state.oil = 65.0

    state.gold = 3350.0

    state.us500_change = 0.80

    state.nasdaq_change = 1.10

    state.dxy_change = -0.30

    state.vix_change = -4.00

    state.us10y_change = -0.50

    state.oil_change = 0.40

    state.gold_change = 0.20

    state.risk_on_off = "RISK_ON"

    state.global_bias = "BULLISH"

    state.confidence = 0.85

    state.add_reason(
        "US500 positivo"
    )

    state.add_reason(
        "Nasdaq positivo"
    )

    state.add_reason(
        "VIX em queda"
    )

    # ==========================================================
    # VERIFICAÇÃO
    # ==========================================================

    print()
    print("DADOS CONTROLADOS")
    print("-" * 72)

    print(
        f"US500        : "
        f"{state.us500}"
    )

    print(
        f"NASDAQ       : "
        f"{state.nasdaq}"
    )

    print(
        f"DXY          : "
        f"{state.dxy}"
    )

    print(
        f"VIX          : "
        f"{state.vix}"
    )

    print(
        f"US10Y        : "
        f"{state.us10y}"
    )

    print(
        f"OIL          : "
        f"{state.oil}"
    )

    print(
        f"GOLD         : "
        f"{state.gold}"
    )

    print(
        f"RISK         : "
        f"{state.risk_on_off}"
    )

    print(
        f"BIAS         : "
        f"{state.global_bias}"
    )

    print(
        f"CONFIDENCE   : "
        f"{state.confidence}"
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
            "Estado deveria estar válido."
        )

    if state.us500 != 6400.0:

        erros.append(
            "US500 incorreto."
        )

    if state.nasdaq != 23700.0:

        erros.append(
            "NASDAQ incorreto."
        )

    if state.dxy != 98.5:

        erros.append(
            "DXY incorreto."
        )

    if state.vix != 15.0:

        erros.append(
            "VIX incorreto."
        )

    if state.risk_on_off != "RISK_ON":

        erros.append(
            "Classificação RISK_ON incorreta."
        )

    if state.global_bias != "BULLISH":

        erros.append(
            "Global bias incorreto."
        )

    if len(state.reasons) != 3:

        erros.append(
            "Quantidade de reasons incorreta."
        )

    # ==========================================================
    # TESTE CLEAR
    # ==========================================================

    state.clear()

    if state.valid:

        erros.append(
            "clear() não resetou valid."
        )

    if state.us500 != 0.0:

        erros.append(
            "clear() não resetou US500."
        )

    if state.nasdaq != 0.0:

        erros.append(
            "clear() não resetou NASDAQ."
        )

    if state.risk_on_off != "NEUTRAL":

        erros.append(
            "clear() não resetou risk_on_off."
        )

    if state.global_bias != "NEUTRAL":

        erros.append(
            "clear() não resetou global_bias."
        )

    if state.confidence != 0.0:

        erros.append(
            "clear() não resetou confidence."
        )

    if state.reasons:

        erros.append(
            "clear() não limpou reasons."
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
        "✅ EXTERNAL MARKET STATE APROVADO"
    )

    print()
    print(
        "Contrato de contexto externo validado."
    )

    return True


def main():

    resultado = executar_teste()

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    if resultado:

        print(
            "🏆 EXTERNAL MARKET STATE APROVADO"
        )

    else:

        print(
            "⚠️ EXTERNAL MARKET STATE "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()