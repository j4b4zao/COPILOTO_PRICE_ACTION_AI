"""
tests/test_provider_symbol_map.py

Teste do mapeamento específico de provider.

RC1
"""

from external_context.providers.provider_symbol_map import (
    ProviderSymbolMap,
)


def main():

    print()
    print("=" * 72)
    print("TESTE PROVIDER SYMBOL MAP")
    print("=" * 72)

    erros = []

    mapping = ProviderSymbolMap(
        "TwelveData"
    )

    print()
    print("PROVIDER")
    print("-" * 72)

    print(
        f"name         : "
        f"{mapping.provider_name}"
    )

    print(
        f"version      : "
        f"{mapping.VERSION}"
    )

    # ----------------------------------------------------------
    # DEFINIR SÍMBOLOS CONTROLADOS
    # ----------------------------------------------------------

    mapping.set_symbol(
        "US500",
        "TEST_US500",
    )

    mapping.set_symbol(
        "NASDAQ",
        "TEST_NASDAQ",
    )

    mapping.set_symbol(
        "DXY",
        "TEST_DXY",
    )

    # ----------------------------------------------------------
    # CONSULTAR
    # ----------------------------------------------------------

    print()
    print("MAPEAMENTO")
    print("-" * 72)

    for asset in (
        "US500",
        "NASDAQ",
        "DXY",
    ):

        symbol = mapping.get_symbol(
            asset
        )

        print(
            f"{asset:<10} : "
            f"{symbol}"
        )

        if symbol is None:

            erros.append(
                f"{asset} não foi encontrado."
            )

    # ----------------------------------------------------------
    # HAS SYMBOL
    # ----------------------------------------------------------

    if not mapping.has_symbol(
        "US500"
    ):

        erros.append(
            "US500 deveria existir."
        )

    if mapping.has_symbol(
        "VIX"
    ):

        erros.append(
            "VIX não deveria existir "
            "neste mapa de teste."
        )

    # ----------------------------------------------------------
    # COUNT
    # ----------------------------------------------------------

    print()
    print(
        f"COUNT        : "
        f"{mapping.count()}"
    )

    if mapping.count() != 3:

        erros.append(
            "Quantidade de símbolos incorreta."
        )

    # ----------------------------------------------------------
    # ALL
    # ----------------------------------------------------------

    print()
    print("ALL")
    print("-" * 72)

    print(
        mapping.all_symbols()
    )

    # ----------------------------------------------------------
    # CLEAR
    # ----------------------------------------------------------

    mapping.clear()

    print()
    print(
        f"COUNT APÓS CLEAR : "
        f"{mapping.count()}"
    )

    if mapping.count() != 0:

        erros.append(
            "clear() não removeu os símbolos."
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

        return

    print(
        "✅ RESULTADO: APROVADO"
    )

    print()
    print(
        "🏆 PROVIDER SYMBOL MAP RC1 APROVADO"
    )


if __name__ == "__main__":

    main()