"""
tests/test_twelvedata_discovery.py

Teste offline do TwelveDataSymbolDiscovery.

RC1
"""

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


def main():

    print()
    print("=" * 72)
    print("TESTE TWELVE DATA SYMBOL DISCOVERY")
    print("=" * 72)

    discovery = (
        TwelveDataSymbolDiscovery(
            api_key="",
        )
    )

    erros = []

    # ==========================================================
    # IDENTIDADE
    # ==========================================================

    print()
    print("DISCOVERY")
    print("-" * 72)

    print(
        f"name         : "
        f"{discovery.NAME}"
    )

    print(
        f"version      : "
        f"{discovery.VERSION}"
    )

    # ==========================================================
    # SEM API KEY
    # ==========================================================

    print()
    print("TESTE SEM API KEY")
    print("-" * 72)

    results = discovery.search(
        "S&P 500"
    )

    print(
        f"results      : "
        f"{results}"
    )

    print(
        f"status       : "
        f"{discovery.last_status}"
    )

    print(
        f"error        : "
        f"{discovery.last_error}"
    )

    if results:

        erros.append(
            "Sem API key não deveria retornar dados."
        )

    if (
        discovery.last_status
        != discovery.STATUS_PROVIDER_ERROR
    ):

        erros.append(
            "Sem API key deveria resultar "
            "em PROVIDER_ERROR."
        )

    if not discovery.last_error:

        erros.append(
            "O erro deveria ser informado."
        )

    # ==========================================================
    # QUERY VAZIA
    # ==========================================================

    print()
    print("TESTE QUERY VAZIA")
    print("-" * 72)

    results = discovery.search(
        ""
    )

    print(
        f"results      : "
        f"{results}"
    )

    print(
        f"status       : "
        f"{discovery.last_status}"
    )

    print(
        f"error        : "
        f"{discovery.last_error}"
    )

    if results:

        erros.append(
            "Query vazia não deveria retornar dados."
        )

    if (
        discovery.last_status
        != discovery.STATUS_INVALID_QUERY
    ):

        erros.append(
            "Query vazia deveria gerar "
            "INVALID_QUERY."
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

        return

    print(
        "✅ RESULTADO: APROVADO"
    )

    print()
    print(
        "🏆 TWELVE DATA DISCOVERY "
        "OFFLINE RC1 APROVADO"
    )


if __name__ == "__main__":

    main()