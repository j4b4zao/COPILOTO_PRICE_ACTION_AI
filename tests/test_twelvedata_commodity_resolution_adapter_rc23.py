"""
tests/test_twelvedata_commodity_resolution_adapter_rc23.py

Teste isolado do Commodity Resolution Adapter RC2.3.
"""

from external_context.providers.twelvedata_commodity_resolution_adapter import (
    TwelveDataCommodityResolutionAdapter,
)


class FakeDiscovery:

    def __init__(
        self,
        responses,
    ):
        self.responses = responses

    def discover(
        self,
        internal_symbol,
    ):
        return self.responses.get(
            internal_symbol,
            {
                "status": "NOT_FOUND",
                "error": "Não encontrado.",
                "results": [],
            },
        )


def main():

    print("=" * 72)
    print(
        "TESTE TWELVE DATA COMMODITY "
        "RESOLUTION ADAPTER RC2.3"
    )
    print("=" * 72)

    # ==========================================================
    # MAPPED OIL
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: OIL → WTI/USD")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol": "WTI/USD",
                        "name": "Crude Oil WTI Spot",
                        "category":
                            "Energy Resource",
                    }
                ],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "MAPPED"
    assert result["symbol"] == "WTI/USD"
    assert result["resolved"] is True

    print("✅ OIL → WTI/USD APROVADO")

    # ==========================================================
    # MAPPED GOLD
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: GOLD → XAU/USD")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "GOLD": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol": "XAU/USD",
                        "name": "Gold Spot",
                        "category":
                            "Precious Metal",
                    }
                ],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "GOLD"
    )

    print(result)

    assert result["status"] == "MAPPED"
    assert result["symbol"] == "XAU/USD"
    assert result["resolved"] is True

    print("✅ GOLD → XAU/USD APROVADO")

    # ==========================================================
    # NOT FOUND
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: NOT_FOUND")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "NOT_FOUND",
                "error": "Nenhuma commodity encontrada.",
                "results": [],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "NOT_FOUND"
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ NOT_FOUND BLOQUEADO")

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: UNAVAILABLE")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "UNAVAILABLE",
                "error": "Plano sem acesso.",
                "results": [],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "UNAVAILABLE"
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ UNAVAILABLE BLOQUEADO")

    # ==========================================================
    # PROVIDER ERROR
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: PROVIDER_ERROR")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "PROVIDER_ERROR",
                "error": "API indisponível.",
                "results": [],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "PROVIDER_ERROR"
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ PROVIDER_ERROR BLOQUEADO")

    # ==========================================================
    # AMBIGUOUS
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: AMBIGUOUS")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol": "WTI/USD",
                        "name": "Crude Oil WTI Spot",
                    },
                    {
                        "symbol": "WTI2/USD",
                        "name": "Another WTI",
                    },
                ],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "AMBIGUOUS"
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ AMBIGUOUS BLOQUEADO")

    # ==========================================================
    # FOUND SEM SYMBOL
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: MAPPED SEM SYMBOL")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "name": "Crude Oil WTI Spot",
                    }
                ],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "NOT_FOUND"
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ CANDIDATO SEM SYMBOL BLOQUEADO")

    # ==========================================================
    # UNKNOWN STATUS
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: STATUS DESCONHECIDO")
    print("=" * 72)

    discovery = FakeDiscovery(
        {
            "OIL": {
                "status": "UNKNOWN_STATUS",
                "error": "",
                "results": [],
            }
        }
    )

    adapter = (
        TwelveDataCommodityResolutionAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "PROVIDER_ERROR"
    assert result["resolved"] is False

    print("✅ UNKNOWN STATUS BLOQUEADO")

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: CLEAR")
    print("=" * 72)

    adapter.clear()

    result = adapter.snapshot()

    print(result)

    assert result["internal_symbol"] == ""
    assert result["status"] == ""
    assert result["symbol"] is None
    assert result["resolved"] is False
    assert result["reason"] == ""
    assert result["metadata"] == {}

    print("✅ CLEAR APROVADO")

    # ==========================================================
    # FINAL
    # ==========================================================

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print()
    print(
        "🏆 TWELVE DATA COMMODITY "
        "RESOLUTION ADAPTER RC2.3 APROVADO"
    )


if __name__ == "__main__":
    main()