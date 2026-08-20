"""
tests/test_symbol_resolution_engine_rc21.py

Teste offline do SymbolResolutionEngine RC2.1.

Não utiliza API.
Não consome créditos.
"""

from external_context.providers.symbol_resolution_engine import (
    SymbolResolutionEngine,
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


def teste_found():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: FOUND"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        provider_name="TwelveData",
        required_symbols=REQUIRED,
    )

    result = engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
        reason="Símbolo validado.",
    )

    print()
    print(
        f"internal   : "
        f"{result.internal_symbol}"
    )

    print(
        f"candidate  : "
        f"{result.candidate_symbol}"
    )

    print(
        f"mapped     : "
        f"{result.mapped_symbol}"
    )

    print(
        f"status     : "
        f"{result.final_status}"
    )

    print(
        f"resolved   : "
        f"{result.resolved}"
    )

    assert (
        result.resolved
        is True
    )

    assert (
        result.mapped_symbol
        == "TEST_NASDAQ"
    )

    assert (
        result.final_status
        == "MAPPED"
    )

    assert (
        engine.count()
        == 1
    )

    print(
        "✅ FOUND APROVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: UNAVAILABLE"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        provider_name="TwelveData",
        required_symbols=REQUIRED,
    )

    result = engine.resolve(
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason=(
            "S&P 500 disponível somente "
            "em plano Grow/Venture."
        ),
        metadata={
            "candidate": "SPX",
            "type": "Index",
        },
    )

    print()
    print(
        f"candidate  : "
        f"{result.candidate_symbol}"
    )

    print(
        f"mapped     : "
        f"{result.mapped_symbol}"
    )

    print(
        f"status     : "
        f"{result.final_status}"
    )

    print(
        f"resolved   : "
        f"{result.resolved}"
    )

    print(
        f"reason     : "
        f"{result.reason}"
    )

    assert (
        result.candidate_symbol
        == "SPX"
    )

    assert (
        result.mapped_symbol
        is None
    )

    assert (
        result.final_status
        == "UNAVAILABLE"
    )

    assert (
        result.resolved
        is False
    )

    assert (
        "Grow/Venture"
        in result.reason
    )

    assert (
        engine.count()
        == 0
    )

    assert (
        "US500"
        in engine.unavailable()
    )

    print(
        "✅ UNAVAILABLE APROVADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: NOT_FOUND"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        "TwelveData",
        REQUIRED,
    )

    result = engine.resolve(
        internal_symbol="DXY",
        provider_symbol=None,
        discovery_status="NOT_FOUND",
        reason="Símbolo não encontrado.",
    )

    assert (
        result.resolved
        is False
    )

    assert (
        result.mapped_symbol
        is None
    )

    assert (
        result.final_status
        == "NOT_FOUND"
    )

    print(
        "✅ NOT_FOUND APROVADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: PROVIDER_ERROR"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        "TwelveData",
        REQUIRED,
    )

    result = engine.resolve(
        internal_symbol="VIX",
        provider_symbol=None,
        discovery_status="PROVIDER_ERROR",
        reason="Provider indisponível.",
    )

    assert (
        result.resolved
        is False
    )

    assert (
        result.mapped_symbol
        is None
    )

    assert (
        result.final_status
        == "PROVIDER_ERROR"
    )

    assert (
        "VIX"
        in engine.provider_errors()
    )

    print(
        "✅ PROVIDER_ERROR APROVADO"
    )


def teste_resolve_many():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: RESOLVE MANY"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        "TwelveData",
        REQUIRED,
    )

    discoveries = [

        {
            "internal_symbol": "NASDAQ",
            "provider_symbol": "TEST_NASDAQ",
            "status": "FOUND",
            "reason": "Encontrado.",
        },

        {
            "internal_symbol": "US500",
            "provider_symbol": "SPX",
            "status": "UNAVAILABLE",
            "reason": "Plano sem acesso.",
        },

        {
            "internal_symbol": "DXY",
            "provider_symbol": None,
            "status": "NOT_FOUND",
            "reason": "Não encontrado.",
        },

        {
            "internal_symbol": "VIX",
            "provider_symbol": None,
            "status": "PROVIDER_ERROR",
            "reason": "Erro provider.",
        },
    ]

    results = engine.resolve_many(
        discoveries
    )

    print()

    for result in results:

        print(
            f"{result.internal_symbol:8} "
            f"| "
            f"{result.final_status:16} "
            f"| "
            f"{str(result.mapped_symbol)}"
        )

    assert (
        len(results)
        == 4
    )

    assert (
        engine.count()
        == 1
    )

    assert (
        engine.resolved_symbols()
        == {
            "NASDAQ": "TEST_NASDAQ"
        }
    )

    assert (
        engine.unavailable()
        == ["US500"]
    )

    assert (
        "VIX"
        in engine.provider_errors()
    )

    assert (
        engine.is_complete()
        is False
    )

    print(
        "✅ RESOLVE MANY APROVADO"
    )


def teste_snapshot():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: SNAPSHOT"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        "TwelveData",
        REQUIRED,
    )

    engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
    )

    engine.resolve(
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason="Plano sem acesso.",
    )

    snapshot = (
        engine.snapshot()
    )

    print()

    for key, value in snapshot.items():

        print(
            f"{key:18}: {value}"
        )

    assert (
        snapshot["name"]
        == "SymbolResolutionEngine"
    )

    assert (
        snapshot["version"]
        == "RC2.1"
    )

    assert (
        snapshot["provider"]
        == "TwelveData"
    )

    assert (
        snapshot["count"]
        == 1
    )

    assert (
        snapshot["complete"]
        is False
    )

    assert (
        snapshot["resolved"]["NASDAQ"]
        == "TEST_NASDAQ"
    )

    assert (
        "US500"
        in snapshot["unavailable"]
    )

    assert (
        snapshot["results"]["US500"]
        ["final_status"]
        == "UNAVAILABLE"
    )

    print(
        "✅ SNAPSHOT APROVADO"
    )


def teste_clear():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE: CLEAR"
    )
    print("=" * 72)

    engine = SymbolResolutionEngine(
        "TwelveData",
        REQUIRED,
    )

    engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
    )

    engine.resolve(
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason="Plano sem acesso.",
    )

    assert (
        engine.count()
        == 1
    )

    engine.clear()

    print()
    print(
        f"count   : {engine.count()}"
    )

    print(
        f"results : {engine.results}"
    )

    print(
        f"symbols : "
        f"{engine.resolved_symbols()}"
    )

    assert (
        engine.count()
        == 0
    )

    assert (
        engine.results
        == {}
    )

    assert (
        engine.resolved_symbols()
        == {}
    )

    assert (
        engine.unavailable()
        == []
    )

    print(
        "✅ CLEAR APROVADO"
    )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL RESOLUTION ENGINE RC2.1"
    )
    print("=" * 72)

    teste_found()

    teste_unavailable()

    teste_not_found()

    teste_provider_error()

    teste_resolve_many()

    teste_snapshot()

    teste_clear()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL RESOLUTION ENGINE "
        "RC2.1 APROVADO"
    )


if __name__ == "__main__":

    main()