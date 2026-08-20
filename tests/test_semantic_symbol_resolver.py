from external_context.providers.semantic_symbol_resolver import (
    SemanticSymbolResolver,
)


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SEMANTIC SYMBOL RESOLVER RC2.3"
    )
    print("=" * 72)

    resolver = (
        SemanticSymbolResolver(
            min_confidence=0.80
        )
    )

    # ==========================================================
    # MAPPED
    # ==========================================================

    print()
    print(
        "TESTE: CANDIDATO VÁLIDO"
    )
    print("-" * 72)

    result = resolver.resolve(
        "NASDAQ",
        [
            {
                "symbol": "TEST_NASDAQ",
                "name": (
                    "Nasdaq Composite Index"
                ),
                "type": "Index",
                "country": "United States",
            }
        ],
    )

    print(result)

    assert (
        result["status"]
        == "MAPPED"
    )

    assert (
        result["symbol"]
        == "TEST_NASDAQ"
    )

    assert (
        result["confidence"]
        >= 0.80
    )

    print(
        "✅ MAPPED APROVADO"
    )

    # ==========================================================
    # UNRESOLVED
    # ==========================================================

    print()
    print(
        "TESTE: CANDIDATO SEM CONFIANÇA"
    )
    print("-" * 72)

    result = resolver.resolve(
        "NASDAQ",
        [
            {
                "symbol": "TEST",
                "name": "Nasdaq ETF",
                "type": "Index",
                "country": "United States",
            }
        ],
    )

    print(result)

    assert (
        result["status"]
        == "UNRESOLVED"
    )

    assert (
        result["symbol"]
        is None
    )

    print(
        "✅ UNRESOLVED APROVADO"
    )

    # ==========================================================
    # AMBIGUOUS
    # ==========================================================

    print()
    print(
        "TESTE: AMBIGUIDADE"
    )
    print("-" * 72)

    result = resolver.resolve(
        "NASDAQ",
        [
            {
                "symbol": "TEST_A",
                "name": (
                    "Nasdaq Composite Index"
                ),
                "type": "Index",
                "country": "United States",
            },
            {
                "symbol": "TEST_B",
                "name": (
                    "Nasdaq Composite Index"
                ),
                "type": "Index",
                "country": "United States",
            },
        ],
    )

    print(result)

    assert (
        result["status"]
        == "AMBIGUOUS"
    )

    assert (
        result["symbol"]
        is None
    )

    print(
        "✅ AMBIGUOUS APROVADO"
    )

    # ==========================================================
    # EMPTY
    # ==========================================================

    print()
    print(
        "TESTE: SEM CANDIDATOS"
    )
    print("-" * 72)

    result = resolver.resolve(
        "NASDAQ",
        [],
    )

    print(result)

    assert (
        result["status"]
        == "UNRESOLVED"
    )

    print(
        "✅ EMPTY APROVADO"
    )

    # ==========================================================
    # RESULTADO
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SEMANTIC SYMBOL RESOLVER "
        "RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()