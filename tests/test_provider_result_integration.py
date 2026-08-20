"""
tests/test_provider_result_integration.py

Teste de integração:

Provider
    ↓
ProviderResult
    ↓
Collector
    ↓
ExternalMarketState
    ↓
ExternalContextEngine

Cenários:

1. Provider disponível + dados válidos
2. Provider indisponível
3. Provider disponível + dados inválidos
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
# PROCESSAR PROVIDER RESULT
# ==============================================================

def processar_provider(
    provider,
):

    result = provider.get_market_data()

    print()
    print("PROVIDER RESULT")
    print("-" * 72)

    print(
        f"valid        : {result.valid}"
    )

    print(
        f"available    : {result.available}"
    )

    print(
        f"source       : {result.source}"
    )

    print(
        f"error        : {result.error}"
    )

    # ----------------------------------------------------------
    # PROVIDER INDISPONÍVEL
    # ----------------------------------------------------------

    if not result.available:

        print()
        print(
            "⚠️ PROVIDER INDISPONÍVEL"
        )

        return None, result

    # ----------------------------------------------------------
    # PROVIDER DISPONÍVEL
    # ----------------------------------------------------------

    collector = ExternalMarketCollector()

    state = collector.coletar(
        result.data
    )

    return state, result


# ==============================================================
# TESTE 1
# ==============================================================

def teste_dados_validos():

    print()
    print("=" * 72)
    print("TESTE: PROVIDER DISPONÍVEL + DADOS VÁLIDOS")
    print("=" * 72)

    provider = MockExternalMarketProvider(
        "RISK_ON"
    )

    state, result = processar_provider(
        provider
    )

    if state is None:

        print(
            "❌ Collector não foi executado."
        )

        return False

    print()
    print("COLLECTOR")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    if not result.available:

        print(
            "❌ Provider deveria estar disponível."
        )

        return False

    if not state.valid:

        print(
            "❌ Dados válidos foram rejeitados."
        )

        for reason in state.reasons:

            print(
                f" - {reason}"
            )

        return False

    # ----------------------------------------------------------
    # ENGINE
    # ----------------------------------------------------------

    ExternalContextEngine().executar(
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

    if state.risk_on_off != "RISK_ON":

        print(
            "❌ RISK_ON esperado."
        )

        return False

    print()
    print(
        "✅ TESTE APROVADO"
    )

    return True


# ==============================================================
# TESTE 2
# ==============================================================

def teste_provider_indisponivel():

    print()
    print("=" * 72)
    print("TESTE: PROVIDER INDISPONÍVEL")
    print("=" * 72)

    provider = MockExternalMarketProvider(
        "UNAVAILABLE"
    )

    state, result = processar_provider(
        provider
    )

    if result.available:

        print(
            "❌ Provider deveria estar indisponível."
        )

        return False

    if state is not None:

        print(
            "❌ Collector não deveria ser executado."
        )

        return False

    print()
    print(
        "✅ PROVIDER BLOQUEADO CORRETAMENTE"
    )

    return True


# ==============================================================
# TESTE 3
# ==============================================================

def teste_dados_invalidos():

    print()
    print("=" * 72)
    print("TESTE: PROVIDER DISPONÍVEL + DADOS INVÁLIDOS")
    print("=" * 72)

    provider = MockExternalMarketProvider(
        "INVALID"
    )

    state, result = processar_provider(
        provider
    )

    if not result.available:

        print(
            "❌ Provider deveria estar disponível."
        )

        return False

    if state is None:

        print(
            "❌ Collector deveria ter sido executado."
        )

        return False

    print()
    print("COLLECTOR")
    print("-" * 72)

    print(
        f"valid        : "
        f"{state.valid}"
    )

    for reason in state.reasons:

        print(
            f"- {reason}"
        )

    if state.valid:

        print()
        print(
            "❌ DADOS INVÁLIDOS FORAM ACEITOS"
        )

        return False

    print()
    print(
        "✅ DADOS INVÁLIDOS BLOQUEADOS"
    )

    return True


# ==============================================================
# MAIN
# ==============================================================

def main():

    valid_ok = teste_dados_validos()

    unavailable_ok = (
        teste_provider_indisponivel()
    )

    invalid_ok = teste_dados_invalidos()

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print(
        f"DADOS VÁLIDOS      : "
        f"{'PASSOU' if valid_ok else 'FALHOU'}"
    )

    print(
        f"PROVIDER INDISP.   : "
        f"{'PASSOU' if unavailable_ok else 'FALHOU'}"
    )

    print(
        f"DADOS INVÁLIDOS    : "
        f"{'PASSOU' if invalid_ok else 'FALHOU'}"
    )

    print()

    if (
        valid_ok
        and unavailable_ok
        and invalid_ok
    ):

        print(
            "🏆 PROVIDER RESULT "
            "INTEGRATION RC1 APROVADO"
        )

    else:

        print(
            "⚠️ PROVIDER RESULT "
            "INTEGRATION PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()