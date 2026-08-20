"""
tests/test_symbol_mapper_incomplete.py

Teste de segurança do SymbolMapper.

Simula um provider que não possui
um dos ativos necessários.

RC1
"""

from external_context.providers.symbol_discovery import (
    SymbolDiscovery,
)

from external_context.providers.symbol_mapper import (
    SymbolMapper,
)

from external_context.providers.symbol_map import (
    ExternalSymbolMap,
)


class IncompleteSymbolDiscovery(SymbolDiscovery):

    NAME = "IncompleteSymbolDiscovery"

    VERSION = "RC1"

    SYMBOLS = (
        {
            "symbol": "TEST_US500",
            "name": "Test S&P 500",
            "type": "INDEX",
            "exchange": "TEST",
        },
        {
            "symbol": "TEST_NASDAQ",
            "name": "Test Nasdaq",
            "type": "INDEX",
            "exchange": "TEST",
        },
        {
            "symbol": "TEST_DXY",
            "name": "Test US Dollar Index",
            "type": "INDEX",
            "exchange": "TEST",
        },
        {
            "symbol": "TEST_VIX",
            "name": "Test Volatility Index",
            "type": "INDEX",
            "exchange": "TEST",
        },

        # US10Y INTENCIONALMENTE AUSENTE

        {
            "symbol": "TEST_OIL",
            "name": "Test Oil",
            "type": "COMMODITY",
            "exchange": "TEST",
        },
        {
            "symbol": "TEST_GOLD",
            "name": "Test Gold",
            "type": "COMMODITY",
            "exchange": "TEST",
        },
    )

    # ==========================================================
    # SEARCH
    # ==========================================================

    def search(
        self,
        query: str,
    ) -> list[dict]:

        query = str(
            query
        ).strip().upper()

        if not query:

            return []

        results = []

        for item in self.SYMBOLS:

            symbol = str(
                item["symbol"]
            ).upper()

            name = str(
                item["name"]
            ).upper()

            if (
                query in symbol
                or query in name
            ):

                results.append(
                    dict(item)
                )

        return results

    # ==========================================================
    # VALIDATE
    # ==========================================================

    def validate_symbol(
        self,
        symbol: str,
    ) -> bool:

        symbol = str(
            symbol
        ).strip().upper()

        for item in self.SYMBOLS:

            if (
                item["symbol"].upper()
                == symbol
            ):

                return True

        return False


def main():

    print()
    print("=" * 72)
    print("TESTE SYMBOL MAPPER: MAPA INCOMPLETO")
    print("=" * 72)

    discovery = IncompleteSymbolDiscovery()

    mapper = SymbolMapper(
        discovery=discovery,
        provider_name="IncompleteProvider",
    )

    mapping = mapper.build()

    print()
    print("MAPEAMENTO")
    print("-" * 72)

    for asset in ExternalSymbolMap.ALL:

        symbol = mapping.get_symbol(
            asset
        )

        print(
            f"{asset:<10} : "
            f"{symbol}"
        )

    print()
    print(
        f"COUNT        : "
        f"{mapping.count()}"
    )

    complete = mapper.is_complete(
        mapping
    )

    print(
        f"COMPLETE     : "
        f"{complete}"
    )

    missing = mapper.missing_assets(
        mapping
    )

    print(
        f"MISSING      : "
        f"{missing}"
    )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    erros = []

    if mapping.count() != 6:

        erros.append(
            "O mapa deveria possuir exatamente "
            "6 ativos."
        )

    if complete:

        erros.append(
            "O mapa não poderia ser considerado completo."
        )

    if missing != ["US10Y"]:

        erros.append(
            f"Esperado missing=['US10Y'], "
            f"obtido {missing}"
        )

    # ==========================================================
    # VERIFICAR QUE OS OUTROS CONTINUAM PRESENTES
    # ==========================================================

    expected_present = (
        "US500",
        "NASDAQ",
        "DXY",
        "VIX",
        "OIL",
        "GOLD",
    )

    for asset in expected_present:

        if not mapping.has_symbol(
            asset
        ):

            erros.append(
                f"{asset} deveria estar presente."
            )

    # ==========================================================
    # US10Y DEVE ESTAR AUSENTE
    # ==========================================================

    if mapping.has_symbol(
        "US10Y"
    ):

        erros.append(
            "US10Y deveria estar ausente."
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
        "✅ MAPA INCOMPLETO DETECTADO CORRETAMENTE"
    )

    print()
    print(
        "🏆 SYMBOL MAPPER INCOMPLETE RC1 APROVADO"
    )


if __name__ == "__main__":

    main()