"""
Teste da arquitetura de providers externos.

Fluxo:

Mock Provider
    ↓
ProviderResult
    ↓
ProviderResult.data
    ↓
ExternalMarketCollector
    ↓
ExternalMarketState
    ↓
ExternalContextEngine

Cenários:

- RISK_ON
- RISK_OFF
- NEUTRAL
- INVALID
"""

from external_context.providers.mock_provider import (
    MockExternalMarketProvider,
)

from external_context.external_market_collector import (
    ExternalMarketCollector,
)

from external_context.external_context_engine import (
    ExternalContextEngine,
)


# ==============================================================
# EXECUTAR CENÁRIO
# ==============================================================

def executar_cenario(
    nome,
    esperado_risk,
    esperado_bias,
):

    print()
    print("=" * 72)
    print(
        f"TESTE PROVIDER PIPELINE: {nome}"
    )
    print("=" * 72)

    # ----------------------------------------------------------
    # PROVIDER
    # ----------------------------------------------------------

    provider = MockExternalMarketProvider(
        nome
    )

    resultado_provider = provider.get_market_data()

    print()
    print("PROVIDER")
    print("-" * 72)

    print(
        f"name         : "
        f"{provider.NAME}"
    )

    print(
        f"version      : "
        f"{provider.VERSION}"
    )

    print(
        f"scenario     : "
        f"{provider.scenario}"
    )

    print(
        f"valid        : "
        f"{resultado_provider.valid}"
    )

    print(
        f"available    : "
        f"{resultado_provider.available}"
    )

    print(
        f"source       : "
        f"{resultado_provider.source}"
    )

    print(
        f"timestamp    : "
        f"{resultado_provider.timestamp}"
    )

    # ----------------------------------------------------------
    # PROTEÇÃO DO CONTRATO DO PROVIDER
    # ----------------------------------------------------------

    if not resultado_provider.valid:

        # ------------------------------------------------------
        # CENÁRIO INVALID
        # ------------------------------------------------------

        if nome == "INVALID":

            print()
            print(
                "PROVIDER RESULT"
            )
            print("-" * 72)

            print(
                "Provider retornou resultado inválido."
            )

            print(
                f"error        : "
                f"{resultado_provider.error}"
            )

        else:

            print()
            print(
                "❌ RESULTADO: FALHOU"
            )

            print(
                "Provider deveria retornar "
                "dados válidos."
            )

            print(
                f"error        : "
                f"{resultado_provider.error}"
            )

            return False

    # ----------------------------------------------------------
    # COLLECTOR
    # ----------------------------------------------------------

    collector = ExternalMarketCollector()

    # ----------------------------------------------------------
    # CONTRATO:
    #
    # ProviderResult contém os metadados do provider.
    #
    # O Collector recebe somente o dicionário de dados.
    # ----------------------------------------------------------

    state = collector.coletar(
        resultado_provider.data
    )

    print()
    print("COLLECTOR")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    print(
        f"timestamp    : "
        f"{state.timestamp}"
    )

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

    # ----------------------------------------------------------
    # SE INVALID, NÃO EXECUTAR ENGINE
    # ----------------------------------------------------------

    if nome == "INVALID":

        if state.valid:

            print()
            print(
                "❌ RESULTADO: FALHOU"
            )

            print(
                "Provider inválido foi aceito."
            )

            return False

        print()
        print(
            "✅ DADOS INVÁLIDOS BLOQUEADOS"
        )

        return True

    # ----------------------------------------------------------
    # VALIDAÇÃO DO COLLECTOR
    # ----------------------------------------------------------

    if not state.valid:

        print()
        print(
            "❌ RESULTADO: FALHOU"
        )

        print(
            "Provider retornou dados válidos, "
            "mas Collector rejeitou."
        )

        for reason in state.reasons:

            print(
                f" - {reason}"
            )

        return False

    # ----------------------------------------------------------
    # ENGINE
    # ----------------------------------------------------------

    engine = ExternalContextEngine()

    engine.executar(
        state
    )

    print()
    print("ENGINE")
    print("-" * 72)

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

    # ----------------------------------------------------------
    # VALIDAÇÃO
    # ----------------------------------------------------------

    erros = []

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

    # ----------------------------------------------------------
    # RESULTADO
    # ----------------------------------------------------------

    print()
    print("=" * 72)

    if erros:

        print(
            "❌ RESULTADO: FALHOU"
        )

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

    risk_on_ok = executar_cenario(
        "RISK_ON",
        "RISK_ON",
        "BULLISH",
    )

    risk_off_ok = executar_cenario(
        "RISK_OFF",
        "RISK_OFF",
        "BEARISH",
    )

    neutral_ok = executar_cenario(
        "NEUTRAL",
        "NEUTRAL",
        "NEUTRAL",
    )

    invalid_ok = executar_cenario(
        "INVALID",
        "NEUTRAL",
        "NEUTRAL",
    )

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print(
        f"RISK ON      : "
        f"{'PASSOU' if risk_on_ok else 'FALHOU'}"
    )

    print(
        f"RISK OFF     : "
        f"{'PASSOU' if risk_off_ok else 'FALHOU'}"
    )

    print(
        f"NEUTRAL      : "
        f"{'PASSOU' if neutral_ok else 'FALHOU'}"
    )

    print(
        f"INVALID      : "
        f"{'PASSOU' if invalid_ok else 'FALHOU'}"
    )

    print()

    if (
        risk_on_ok
        and risk_off_ok
        and neutral_ok
        and invalid_ok
    ):

        print(
            "🏆 PROVIDER PIPELINE RC2.3 APROVADO"
        )

    else:

        print(
            "⚠️ PROVIDER PIPELINE "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()