"""
Teste da SemanticSymbolResolutionPipeline RC2.3.

Offline.
Não utiliza API.
Não consome créditos.
"""

from external_context.providers.semantic_symbol_resolution_pipeline import (
    SemanticSymbolResolutionPipeline,
)


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


def teste_mapped():

    print()
    print("=" * 72)
    print(
        "TESTE PIPELINE: MAPPED"
    )
    print("=" * 72)

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    candidates = [

        candidato(
            "NDAQ",
            "Nasdaq, Inc.",
            "Common Stock",
        ),

        candidato(
            "TEST_NASDAQ",
            "Nasdaq Composite Index",
        ),

        candidato(
            "TEST_ETF",
            "Nasdaq Composite ETF",
            "ETF",
        ),
    ]

    result = pipeline.resolve(
        "NASDAQ",
        candidates,
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
        result["status"]
        == "MAPPED"
    )

    assert (
        result["symbol"]
        == "TEST_NASDAQ"
    )

    assert (
        result["resolved"]
        is True
    )

    assert (
        result["accepted_count"]
        == 1
    )

    assert (
        result["rejected_count"]
        == 2
    )

    print(
        "✅ MAPPED APROVADO"
    )


def teste_unresolved():

    print()
    print("=" * 72)
    print(
        "TESTE PIPELINE: UNRESOLVED"
    )
    print("=" * 72)

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    candidates = [

        candidato(
            "TEST_A",
            "Nasdaq ETF",
        ),

        candidato(
            "TEST_B",
            "Nasdaq Fund",
        ),
    ]

    result = pipeline.resolve(
        "NASDAQ",
        candidates,
    )

    print()
    print(
        result
    )

    assert (
        result["status"]
        == "UNRESOLVED"
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        result["resolved"]
        is False
    )

    print(
        "✅ UNRESOLVED APROVADO"
    )


def teste_ambiguous():

    print()
    print("=" * 72)
    print(
        "TESTE PIPELINE: AMBIGUOUS"
    )
    print("=" * 72)

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    candidates = [

        candidato(
            "TEST_A",
            "Nasdaq Composite Index",
        ),

        candidato(
            "TEST_B",
            "Nasdaq Composite Index",
        ),
    ]

    result = pipeline.resolve(
        "NASDAQ",
        candidates,
    )

    print()
    print(
        result
    )

    assert (
        result["status"]
        == "AMBIGUOUS"
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        result["resolved"]
        is False
    )

    assert (
        result["accepted_count"]
        == 2
    )

    print(
        "✅ AMBIGUOUS APROVADO"
    )


def teste_false_positive():

    print()
    print("=" * 72)
    print(
        "TESTE PIPELINE: FALSE POSITIVE"
    )
    print("=" * 72)

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    candidates = [

        candidato(
            "NDAQ",
            "Nasdaq, Inc.",
            "Common Stock",
        ),
    ]

    result = pipeline.resolve(
        "NASDAQ",
        candidates,
    )

    print()
    print(
        result
    )

    assert (
        result["status"]
        == "UNRESOLVED"
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        result["resolved"]
        is False
    )

    assert (
        result["accepted_count"]
        == 0
    )

    assert (
        result["rejected_count"]
        == 1
    )

    print(
        "✅ FALSE POSITIVE BLOQUEADO"
    )


def teste_country_filter():

    print()
    print("=" * 72)
    print(
        "TESTE PIPELINE: COUNTRY FILTER"
    )
    print("=" * 72)

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    candidates = [

        candidato(
            "TEST_FOREIGN",
            "Nasdaq Composite Index",
            "Index",
            "Germany",
        ),

        candidato(
            "TEST_US",
            "Nasdaq Composite Index",
            "Index",
            "United States",
        ),
    ]

    result = pipeline.resolve(
        "NASDAQ",
        candidates,
    )

    print()
    print(
        result
    )

    assert (
        result["status"]
        == "MAPPED"
    )

    assert (
        result["symbol"]
        == "TEST_US"
    )

    assert (
        result["accepted_count"]
        == 1
    )

    assert (
        result["rejected_count"]
        == 1
    )

    print(
        "✅ COUNTRY FILTER APROVADO"
    )


def teste_clear():

    print()
    print("=" * 72)
    print(
        "TESTE PIPELINE: CLEAR"
    )
    print("=" * 72)

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    pipeline.resolve(
        "NASDAQ",
        [
            candidato(
                "TEST_NASDAQ",
                "Nasdaq Composite Index",
            )
        ],
    )

    pipeline.clear()

    result = pipeline.snapshot()

    print()
    print(
        result
    )

    assert (
        result["internal_symbol"]
        == ""
    )

    assert (
        result["status"]
        == ""
    )

    assert (
        result["symbol"]
        is None
    )

    assert (
        result["resolved"]
        is False
    )

    assert (
        result["candidate_count"]
        == 0
    )

    assert (
        result["accepted_count"]
        == 0
    )

    assert (
        result["rejected_count"]
        == 0
    )

    print(
        "✅ CLEAR APROVADO"
    )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SEMANTIC SYMBOL "
        "RESOLUTION PIPELINE RC2.3"
    )
    print("=" * 72)

    teste_mapped()

    teste_unresolved()

    teste_ambiguous()

    teste_false_positive()

    teste_country_filter()

    teste_clear()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SEMANTIC SYMBOL "
        "RESOLUTION PIPELINE "
        "RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()