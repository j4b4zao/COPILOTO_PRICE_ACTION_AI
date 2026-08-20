"""
tests/test_symbol_resolution_provider_rc21.py

Teste offline do SymbolResolutionProvider RC2.1.

Não utiliza API.
Não consome créditos.
"""

from external_context.providers.symbol_resolution_engine import (
    SymbolResolutionEngine,
)

from external_context.providers.symbol_resolution_provider import (
    SymbolResolutionProvider,
)


REQUIRED = [
    "US500",
    "NASDAQ",
    "DXY",
    "VIX",
    "US10Y",
    "OIL",
    "GOLD",
]


class FakeDiscovery:

    NAME = "FakeDiscovery"

    VERSION = "RC2.1"

    def __init__(
        self,
        status,
        results=None,
        error="",
    ):

        self.last_status = status

        self.last_error = error

        self.results = (
            results or []
        )

    def search(
        self,
        query,
    ):

        return list(
            self.results
        )


def criar_provider(
    discovery,
):

    engine = SymbolResolutionEngine(
        provider_name="TwelveData",
        required_symbols=REQUIRED,
    )

    return SymbolResolutionProvider(
        discovery=discovery,
        engine=engine,
    )


def teste_found():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER: FOUND"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            {
                "symbol": "TEST_NASDAQ",
                "name": "Test Nasdaq",
                "type": "Index",
                "exchange": "TEST",
            }
        ],
    )

    provider = criar_provider(
        discovery
    )

    result = provider.resolve(
        "NASDAQ",
        query="TEST_NASDAQ",
    )

    print()
    print(
        f"status : "
        f"{result.final_status}"
    )

    print(
        f"mapped : "
        f"{result.mapped_symbol}"
    )

    assert (
        result.final_status
        == "MAPPED"
    )

    assert (
        result.mapped_symbol
        == "TEST_NASDAQ"
    )

    assert (
        result.resolved
        is True
    )

    print(
        "✅ FOUND APROVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER: UNAVAILABLE"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="UNAVAILABLE",
        error=(
            "Recurso disponível "
            "somente em plano superior."
        ),
    )

    provider = criar_provider(
        discovery
    )

    result = provider.resolve(
        "US500",
        query="SPX",
    )

    print()
    print(
        f"status : "
        f"{result.final_status}"
    )

    print(
        f"mapped : "
        f"{result.mapped_symbol}"
    )

    assert (
        result.final_status
        == "UNAVAILABLE"
    )

    assert (
        result.mapped_symbol
        is None
    )

    assert (
        result.resolved
        is False
    )

    print(
        "✅ UNAVAILABLE APROVADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER: NOT_FOUND"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="NOT_FOUND"
    )

    provider = criar_provider(
        discovery
    )

    result = provider.resolve(
        "DXY"
    )

    assert (
        result.final_status
        == "NOT_FOUND"
    )

    assert (
        result.resolved
        is False
    )

    print(
        "✅ NOT_FOUND APROVADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER: PROVIDER_ERROR"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="PROVIDER_ERROR",
        error=(
            "Provider indisponível."
        ),
    )

    provider = criar_provider(
        discovery
    )

    result = provider.resolve(
        "VIX"
    )

    assert (
        result.final_status
        == "PROVIDER_ERROR"
    )

    assert (
        result.resolved
        is False
    )

    print(
        "✅ PROVIDER_ERROR APROVADO"
    )


def teste_multiplos_exatos():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER: "
        "MÚLTIPLOS CANDIDATOS EXATOS"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            {
                "symbol": "TEST",
                "name": "Test A",
            },
            {
                "symbol": "TEST",
                "name": "Test B",
            },
        ],
    )

    provider = criar_provider(
        discovery
    )

    result = provider.resolve(
        "DXY",
        query="TEST",
    )

    print()
    print(
        f"status : "
        f"{result.final_status}"
    )

    print(
        f"mapped : "
        f"{result.mapped_symbol}"
    )

    assert (
        result.final_status
        == "UNAVAILABLE"
    )

    assert (
        result.mapped_symbol
        is None
    )

    assert (
        result.resolved
        is False
    )

    print(
        "✅ AMBIGUIDADE BLOQUEADA"
    )


def teste_snapshot():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER: SNAPSHOT"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            {
                "symbol": "TEST_NASDAQ",
                "name": "Test Nasdaq",
            }
        ],
    )

    provider = criar_provider(
        discovery
    )

    provider.resolve(
        "NASDAQ",
        query="TEST_NASDAQ",
    )

    snapshot = (
        provider.snapshot()
    )

    print()

    for key, value in snapshot.items():

        print(
            f"{key:12}: {value}"
        )

    assert (
        snapshot["name"]
        == "SymbolResolutionProvider"
    )

    assert (
        snapshot["version"]
        == "RC2.1"
    )

    assert (
        snapshot["engine"]["count"]
        == 1
    )

    print(
        "✅ SNAPSHOT APROVADO"
    )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL RESOLUTION "
        "PROVIDER RC2.1"
    )
    print("=" * 72)

    teste_found()

    teste_unavailable()

    teste_not_found()

    teste_provider_error()

    teste_multiplos_exatos()

    teste_snapshot()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL RESOLUTION PROVIDER "
        "RC2.1 APROVADO"
    )


if __name__ == "__main__":

    main()