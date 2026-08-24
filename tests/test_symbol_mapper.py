"""
tests/test_symbol_mapper.py

Teste da integração:

ExternalSymbolMap
        ↓
SymbolDiscovery
        ↓
ProviderSymbolMap

RC1
"""

from external_context.providers.mock_symbol_discovery import (
    MockSymbolDiscovery,
)

from external_context.providers.symbol_mapper import (
    SymbolMapper,
)

from external_context.providers.symbol_map import (
    ExternalSymbolMap,
)


def main():

    print()
    print("=" * 72)
    print("TESTE SYMBOL MAPPER")
    print("=" * 72)

    discovery = MockSymbolDiscovery()

    mapper = SymbolMapper(
        discovery=discovery,
        provider_name="MockProvider",
    )

    # ==========================================================
    # CONSTRUIR MAPA
    # ==========================================================

    mapping = mapper.build()

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

    # ==========================================================
    # MAPA
    # ==========================================================

    print()
    print("MAPEAMENTO AUTOMÁTICO")
    print("-" * 72)

    for asset in ExternalSymbolMap.ALL:

        symbol = mapping.get_symbol(
            asset
        )

        print(
            f"{asset:<10} : "
            f"{symbol}"
        )

    # ==========================================================
    # QUANTIDADE
    # ==========================================================

    print()
    print(
        f"COUNT        : "
        f"{mapping.count()}"
    )

    # ==========================================================
    # COMPLETO
    # ==========================================================

    complete = mapper.is_complete(
        mapping
    )

    print()
    print(
        f"COMPLETE     : "
        f"{complete}"
    )

    # ==========================================================
    # AUSENTES
    # ==========================================================

    missing = mapper.missing_assets(
        mapping
    )

    print()
    print(
        f"MISSING      : "
        f"{missing}"
    )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    erros = []

    if mapping.count() != 7:

        erros.append(
            "O mapa deveria possuir "
            "os 7 ativos."
        )

    if not complete:

        erros.append(
            "O mapa deveria estar completo."
        )

    if missing:

        erros.append(
            f"Existem ativos ausentes: "
            f"{missing}"
        )

    # ==========================================================
    # VERIFICAR CADA ATIVO
    # ==========================================================

    expected = {
        "US500": "TEST_US500",
        "NASDAQ": "TEST_NASDAQ",
        "DXY": "TEST_DXY",
        "VIX": "TEST_VIX",
        "US10Y": "TEST_US10Y",
        "OIL": "TEST_OIL",
        "GOLD": "TEST_GOLD",
    }

    for asset, expected_symbol in expected.items():

        symbol = mapping.get_symbol(
            asset
        )

        if symbol != expected_symbol:

            erros.append(
                f"{asset}: esperado "
                f"{expected_symbol}, "
                f"obtido {symbol}"
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
        "🏆 SYMBOL MAPPER RC1 APROVADO"
    )


if __name__ == "__main__":

    main()