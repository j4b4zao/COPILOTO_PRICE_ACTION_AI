"""
tests/test_symbol_resolution_provider_rc22.py

Teste do SymbolResolutionProvider RC2.2.

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

    VERSION = "RC2.2"

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


def teste_mapped():

    print()
    print("=" * 72)
    print(
        "TESTE RC2.2: MAPPED"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            {
                "symbol": "NASDAQ",
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
        query="NASDAQ",
    )

    print()
    print(
        f"status   : {result.final_status}"
    )

    print(
        f"mapped   : {result.mapped_symbol}"
    )

    assert (
        result.final_status
        == "MAPPED"
    )

    assert (
        result.mapped_symbol
        == "NASDAQ"
    )

    assert (
        result.resolved
        is True
    )

    print(
        "✅ MAPPED APROVADO"
    )


def teste_unresolved():

    print()
    print("=" * 72)
    print(
        "TESTE RC2.2: UNRESOLVED"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            {
                "symbol": "ABC",
                "name": "ABC",
            },
            {
                "symbol": "XYZ",
                "name": "XYZ",
            },
        ],
    )

    provider = criar_provider(
        discovery
    )

    result = provider.resolve(
        "NASDAQ",
        query="NASDAQ",
    )

    print()
    print(
        f"status   : "
        f"{result.final_status}"
    )

    print(
        f"mapped   : "
        f"{result.mapped_symbol}"
    )

    print(
        f"reason   : "
        f"{result.reason}"
    )

    print(
        f"metadata : "
        f"{result.metadata}"
    )

    assert (
        result.final_status
        == "UNRESOLVED"
    )

    assert (
        result.mapped_symbol
        is None
    )

    assert (
        result.resolved
        is False
    )

    assert (
        result.metadata[
            "candidate_count"
        ]
        == 2
    )

    print(
        "✅ UNRESOLVED APROVADO"
    )


def teste_ambiguous():

    print()
    print("=" * 72)
    print(
        "TESTE RC2.2: AMBIGUOUS"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="FOUND",
        results=[
            {
                "symbol": "TEST",
                "name": "Test A",
                "exchange": "A",
            },
            {
                "symbol": "TEST",
                "name": "Test B",
                "exchange": "B",
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
        f"status   : "
        f"{result.final_status}"
    )

    print(
        f"mapped   : "
        f"{result.mapped_symbol}"
    )

    assert (
        result.final_status
        == "AMBIGUOUS"
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
        "✅ AMBIGUOUS APROVADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE RC2.2: NOT_FOUND"
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


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE RC2.2: UNAVAILABLE"
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
        "US500"
    )

    assert (
        result.final_status
        == "UNAVAILABLE"
    )

    assert (
        result.resolved
        is False
    )

    print(
        "✅ UNAVAILABLE APROVADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE RC2.2: PROVIDER_ERROR"
    )
    print("=" * 72)

    discovery = FakeDiscovery(
        status="PROVIDER_ERROR",
        error="Erro de autenticação.",
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


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL RESOLUTION "
        "PROVIDER RC2.2"
    )
    print("=" * 72)

    teste_mapped()

    teste_unresolved()

    teste_ambiguous()

    teste_not_found()

    teste_unavailable()

    teste_provider_error()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL RESOLUTION PROVIDER "
        "RC2.2 APROVADO"
    )


if __name__ == "__main__":

    main()