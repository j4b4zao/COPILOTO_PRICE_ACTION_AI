"""
tests/test_provider_result.py

Teste do contrato ProviderResult.

RC1
"""

from external_context.providers.mock_provider import (
    MockExternalMarketProvider,
)


def executar():

    print()
    print("=" * 72)
    print("TESTE PROVIDER RESULT")
    print("=" * 72)

    erros = []

    # ==========================================================
    # PROVIDER DISPONÍVEL
    # ==========================================================

    print()
    print("PROVIDER DISPONÍVEL")
    print("-" * 72)

    provider = MockExternalMarketProvider(
        "RISK_ON"
    )

    result = provider.get_market_data()

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

    if not result.valid:

        erros.append(
            "Provider válido deveria ter valid=True."
        )

    if not result.available:

        erros.append(
            "Provider válido deveria estar disponível."
        )

    if not result.data:

        erros.append(
            "Provider válido deveria retornar dados."
        )

    # ==========================================================
    # PROVIDER INDISPONÍVEL
    # ==========================================================

    print()
    print("PROVIDER INDISPONÍVEL")
    print("-" * 72)

    provider = MockExternalMarketProvider(
        "UNAVAILABLE"
    )

    result = provider.get_market_data()

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

    if result.valid:

        erros.append(
            "Provider indisponível não pode ser válido."
        )

    if result.available:

        erros.append(
            "Provider indisponível não pode "
            "estar disponível."
        )

    if not result.error:

        erros.append(
            "Falha do provider deveria possuir erro."
        )

    # ==========================================================
    # DADOS INVÁLIDOS
    # ==========================================================

    print()
    print("DADOS INVÁLIDOS")
    print("-" * 72)

    provider = MockExternalMarketProvider(
        "INVALID"
    )

    result = provider.get_market_data()

    print(
        f"valid        : {result.valid}"
    )

    print(
        f"available    : {result.available}"
    )

    print(
        f"data         : "
        f"{len(result.data)} campos"
    )

    if not result.valid:

        erros.append(
            "Provider deveria entregar o lote "
            "para o Collector validar."
        )

    if not result.available:

        erros.append(
            "Provider deveria estar disponível."
        )

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print("TESTE CLEAR")
    print("-" * 72)

    result.clear()

    print(
        f"valid        : {result.valid}"
    )

    print(
        f"available    : {result.available}"
    )

    print(
        f"data         : {result.data}"
    )

    print(
        f"error        : {result.error}"
    )

    if result.valid:

        erros.append(
            "clear() não resetou valid."
        )

    if result.available:

        erros.append(
            "clear() não resetou available."
        )

    if result.data:

        erros.append(
            "clear() não limpou data."
        )

    if result.error:

        erros.append(
            "clear() não limpou error."
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

        for erro in erros:

            print(
                f" - {erro}"
            )

        return False

    print(
        "✅ PROVIDER RESULT APROVADO"
    )

    return True


def main():

    resultado = executar()

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    if resultado:

        print(
            "🏆 PROVIDER RESULT RC1 APROVADO"
        )

    else:

        print(
            "⚠️ PROVIDER RESULT "
            "PRECISA DE CORREÇÃO"
        )


if __name__ == "__main__":

    main()