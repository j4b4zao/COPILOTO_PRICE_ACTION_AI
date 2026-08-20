"""
external_context/providers/mock_symbol_discovery.py

Mock Symbol Discovery.

RC1

Não utiliza internet.

Serve para testar o contrato de descoberta
de instrumentos.
"""

from external_context.providers.symbol_discovery import (
    SymbolDiscovery,
)


class MockSymbolDiscovery(SymbolDiscovery):

    NAME = "MockSymbolDiscovery"

    VERSION = "RC1"

    # ==========================================================
    # CATÁLOGO CONTROLADO
    # ==========================================================

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
        {
            "symbol": "TEST_US10Y",
            "name": "Test US 10Y",
            "type": "BOND",
            "exchange": "TEST",
        },
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

        if not symbol:

            return False

        for item in self.SYMBOLS:

            if (
                item["symbol"].upper()
                == symbol
            ):

                return True

        return False