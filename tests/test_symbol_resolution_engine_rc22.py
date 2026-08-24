"""
tests/test_symbol_resolution_engine_rc22.py

Teste offline do SymbolResolutionEngine RC2.2.

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


def criar_engine():

    return SymbolResolutionEngine(
        provider_name="TwelveData",
        required_symbols=REQUIRED,
    )


def teste_mapped():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: MAPPED"
    )
    print("=" * 72)

    engine = criar_engine()

    result = engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="MAPPED",
        reason="Símbolo validado.",
    )

    print()
    print(
        f"status   : {result.final_status}"
    )

    print(
        f"mapped   : {result.mapped_symbol}"
    )

    print(
        f"resolved : {result.resolved}"
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

    assert (
        engine.count()
        == 1
    )

    print(
        "✅ MAPPED APROVADO"
    )


def teste_unresolved():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: UNRESOLVED"
    )
    print("=" * 72)

    engine = criar_engine()

    result = engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol=None,
        discovery_status="UNRESOLVED",
        reason=(
            "Candidatos encontrados, "
            "mas nenhum possui símbolo "
            "exato."
        ),
        metadata={
            "candidate_count": 30,
            "query": "NASDAQ",
        },
    )

    print()
    print(
        f"status   : {result.final_status}"
    )

    print(
        f"mapped   : {result.mapped_symbol}"
    )

    print(
        f"resolved : {result.resolved}"
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
        engine.count()
        == 0
    )

    assert (
        result.metadata[
            "candidate_count"
        ]
        == 30
    )

    print(
        "✅ UNRESOLVED APROVADO"
    )


def teste_ambiguous():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: AMBIGUOUS"
    )
    print("=" * 72)

    engine = criar_engine()

    result = engine.resolve(
        internal_symbol="DXY",
        provider_symbol=None,
        discovery_status="AMBIGUOUS",
        reason=(
            "Múltiplos candidatos exatos."
        ),
        metadata={
            "candidate_count": 2,
            "candidates": [
                {
                    "symbol": "TEST",
                    "exchange": "A",
                },
                {
                    "symbol": "TEST",
                    "exchange": "B",
                },
            ],
        },
    )

    print()
    print(
        f"status   : {result.final_status}"
    )

    print(
        f"mapped   : {result.mapped_symbol}"
    )

    print(
        f"resolved : {result.resolved}"
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

    assert (
        engine.count()
        == 0
    )

    print(
        "✅ AMBIGUOUS APROVADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: NOT_FOUND"
    )
    print("=" * 72)

    engine = criar_engine()

    result = engine.resolve(
        internal_symbol="DXY",
        provider_symbol=None,
        discovery_status="NOT_FOUND",
        reason="Não encontrado.",
    )

    assert (
        result.final_status
        == "NOT_FOUND"
    )

    assert (
        result.resolved
        is False
    )

    assert (
        result.mapped_symbol
        is None
    )

    print(
        "✅ NOT_FOUND APROVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: UNAVAILABLE"
    )
    print("=" * 72)

    engine = criar_engine()

    result = engine.resolve(
        internal_symbol="US500",
        provider_symbol=None,
        discovery_status="UNAVAILABLE",
        reason=(
            "S&P 500 disponível somente "
            "em plano Grow/Venture."
        ),
        metadata={
            "candidate": "SPX",
        },
    )

    print()
    print(
        f"candidate: "
        f"{result.candidate_symbol}"
    )

    print(
        f"status   : "
        f"{result.final_status}"
    )

    print(
        f"mapped   : "
        f"{result.mapped_symbol}"
    )

    assert (
        result.candidate_symbol
        == "SPX"
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


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: PROVIDER_ERROR"
    )
    print("=" * 72)

    engine = criar_engine()

    result = engine.resolve(
        internal_symbol="VIX",
        provider_symbol=None,
        discovery_status="PROVIDER_ERROR",
        reason="Provider indisponível.",
    )

    assert (
        result.final_status
        == "PROVIDER_ERROR"
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
        "VIX"
        in engine.provider_errors()
    )

    print(
        "✅ PROVIDER_ERROR APROVADO"
    )


def teste_mixed():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: CENÁRIO MISTO"
    )
    print("=" * 72)

    engine = criar_engine()

    engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="MAPPED",
    )

    engine.resolve(
        internal_symbol="US500",
        provider_symbol=None,
        discovery_status="UNRESOLVED",
        reason="Sem correspondência exata.",
    )

    engine.resolve(
        internal_symbol="DXY",
        provider_symbol=None,
        discovery_status="AMBIGUOUS",
        reason="Múltiplos candidatos.",
    )

    engine.resolve(
        internal_symbol="VIX",
        provider_symbol=None,
        discovery_status="PROVIDER_ERROR",
        reason="Provider indisponível.",
    )

    print()
    print(
        "RESOLVIDOS"
    )
    print("-" * 72)

    print(
        engine.resolved_symbols()
    )

    print()
    print(
        "SNAPSHOT"
    )
    print("-" * 72)

    snapshot = engine.snapshot()

    print(
        snapshot
    )

    assert (
        engine.resolved_symbols()
        == {
            "NASDAQ": "TEST_NASDAQ"
        }
    )

    assert (
        engine.count()
        == 1
    )

    assert (
        engine.is_complete()
        is False
    )

    assert (
        snapshot["results"]["US500"]
        ["final_status"]
        == "UNRESOLVED"
    )

    assert (
        snapshot["results"]["DXY"]
        ["final_status"]
        == "AMBIGUOUS"
    )

    assert (
        snapshot["results"]["VIX"]
        ["final_status"]
        == "PROVIDER_ERROR"
    )

    print(
        "✅ CENÁRIO MISTO APROVADO"
    )


def teste_clear():

    print()
    print("=" * 72)
    print(
        "TESTE ENGINE RC2.2: CLEAR"
    )
    print("=" * 72)

    engine = criar_engine()

    engine.resolve(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="MAPPED",
    )

    engine.resolve(
        internal_symbol="US500",
        provider_symbol=None,
        discovery_status="UNRESOLVED",
        reason="Teste.",
    )

    engine.clear()

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

    print(
        "✅ CLEAR APROVADO"
    )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL RESOLUTION "
        "ENGINE RC2.2"
    )
    print("=" * 72)

    teste_mapped()

    teste_unresolved()

    teste_ambiguous()

    teste_not_found()

    teste_unavailable()

    teste_provider_error()

    teste_mixed()

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
        "RC2.2 APROVADO"
    )


if __name__ == "__main__":

    main()