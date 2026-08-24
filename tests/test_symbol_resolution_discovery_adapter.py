"""
tests/test_symbol_resolution_discovery_adapter.py

Teste do SymbolResolutionDiscoveryAdapter RC2.3.

Offline.
Não utiliza API.
Não consome créditos da Twelve Data.
"""

from external_context.providers.symbol_resolution_discovery_adapter import (
    SymbolResolutionDiscoveryAdapter,
)


class FakeDiscovery:

    NAME = "FakeDiscovery"

    VERSION = "RC2.3"

    def __init__(
        self,
        status="FOUND",
        results=None,
        error="",
    ):

        self.status = status

        self.results = (
            results
            if results is not None
            else []
        )

        self.error = error

        self.last_query = ""

    def search(
        self,
        query: str,
    ) -> dict:

        self.last_query = query

        return {
            "status": self.status,
            "error": self.error,
            "results": list(
                self.results
            ),
        }


def candidato(
    symbol,
    name,
    instrument_type="Index",
    country="United States",
):

    return {
        "symbol": symbol,
        "name": name,
        "type": instrument_type,
        "exchange": "TEST",
        "country": country,
        "currency": "USD",
    }


def teste_found_mapped():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: FOUND → MAPPED"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            candidato(
                "NDAQ",
                "Nasdaq, Inc.",
                "Common Stock",
            ),
            candidato(
                "TEST_NASDAQ",
                "Nasdaq Composite Index",
            ),
        ],
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "NASDAQ"
    )

    print()
    print(
        "DISCOVERY"
    )
    print("-" * 72)

    print(
        discovery.last_query
    )

    print()
    print(
        "RESULTADO"
    )
    print("-" * 72)

    print(
        result
    )

    assert (
        discovery.last_query
        == "NASDAQ"
    )

    assert (
        result[
            "discovery_status"
        ]
        == "FOUND"
    )

    assert (
        result[
            "resolution"
        ][
            "status"
        ]
        == "MAPPED"
    )

    assert (
        result[
            "resolution"
        ][
            "symbol"
        ]
        == "TEST_NASDAQ"
    )

    assert (
        result[
            "resolved"
        ]
        is True
    )

    print(
        "✅ FOUND → MAPPED APROVADO"
    )


def teste_found_unresolved():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: FOUND → UNRESOLVED"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            candidato(
                "NDAQ",
                "Nasdaq, Inc.",
                "Common Stock",
            ),
        ],
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "NASDAQ"
    )

    print()
    print(
        result
    )

    assert (
        result[
            "discovery_status"
        ]
        == "FOUND"
    )

    assert (
        result[
            "resolution"
        ][
            "status"
        ]
        == "UNRESOLVED"
    )

    assert (
        result[
            "resolution"
        ][
            "symbol"
        ]
        is None
    )

    assert (
        result[
            "resolved"
        ]
        is False
    )

    print(
        "✅ FALSE POSITIVE → "
        "UNRESOLVED APROVADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: NOT_FOUND"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="NOT_FOUND",
        results=[],
        error="Nenhum candidato encontrado.",
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "NASDAQ"
    )

    print()
    print(
        result
    )

    assert (
        result[
            "discovery_status"
        ]
        == "NOT_FOUND"
    )

    assert (
        result[
            "resolution"
        ]
        == {}
    )

    assert (
        result[
            "resolved"
        ]
        is False
    )

    assert (
        result[
            "discovery_error"
        ]
        == "Nenhum candidato encontrado."
    )

    print(
        "✅ NOT_FOUND PRESERVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: UNAVAILABLE"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="UNAVAILABLE",
        results=[],
        error=(
            "S&P 500 disponível "
            "somente em plano Grow/Venture."
        ),
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "US500"
    )

    print()
    print(
        result
    )

    assert (
        result[
            "discovery_status"
        ]
        == "UNAVAILABLE"
    )

    assert (
        result[
            "resolution"
        ]
        == {}
    )

    assert (
        result[
            "resolved"
        ]
        is False
    )

    print(
        "✅ UNAVAILABLE PRESERVADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: PROVIDER_ERROR"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="PROVIDER_ERROR",
        results=[],
        error=(
            "Twelve Data indisponível."
        ),
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "NASDAQ"
    )

    print()
    print(
        result
    )

    assert (
        result[
            "discovery_status"
        ]
        == "PROVIDER_ERROR"
    )

    assert (
        result[
            "resolution"
        ]
        == {}
    )

    assert (
        result[
            "resolved"
        ]
        is False
    )

    assert (
        result[
            "discovery_error"
        ]
        == "Twelve Data indisponível."
    )

    print(
        "✅ PROVIDER_ERROR PRESERVADO"
    )


def teste_unknown_status():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: STATUS DESCONHECIDO"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="UNKNOWN",
        results=[],
        error="",
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    result = adapter.resolve(
        "NASDAQ"
    )

    print()
    print(
        result
    )

    assert (
        result[
            "discovery_status"
        ]
        == "PROVIDER_ERROR"
    )

    assert (
        result[
            "resolved"
        ]
        is False
    )

    assert (
        result[
            "discovery_error"
        ]
        != ""
    )

    print(
        "✅ UNKNOWN STATUS BLOQUEADO"
    )


def teste_clear():

    print()
    print("=" * 72)
    print(
        "TESTE ADAPTER: CLEAR"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            candidato(
                "TEST_NASDAQ",
                "Nasdaq Composite Index",
            )
        ],
    )

    adapter = (
        SymbolResolutionDiscoveryAdapter(
            discovery
        )
    )

    adapter.resolve(
        "NASDAQ"
    )

    adapter.clear()

    result = adapter.snapshot()

    print()
    print(
        result
    )

    assert (
        result[
            "internal_symbol"
        ]
        == ""
    )

    assert (
        result[
            "discovery_status"
        ]
        == ""
    )

    assert (
        result[
            "discovery_error"
        ]
        == ""
    )

    assert (
        result[
            "candidate_count"
        ]
        == 0
    )

    assert (
        result[
            "resolution"
        ]
        == {}
    )

    assert (
        result[
            "resolved"
        ]
        is False
    )

    print(
        "✅ CLEAR APROVADO"
    )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL RESOLUTION "
        "DISCOVERY ADAPTER RC2.3"
    )
    print("=" * 72)

    teste_found_mapped()

    teste_found_unresolved()

    teste_not_found()

    teste_unavailable()

    teste_provider_error()

    teste_unknown_status()

    teste_clear()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL RESOLUTION "
        "DISCOVERY ADAPTER "
        "RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()