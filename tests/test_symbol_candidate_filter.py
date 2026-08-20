from external_context.providers.symbol_candidate_filter import (
    SymbolCandidateFilter,
)


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL CANDIDATE FILTER RC2.3"
    )
    print("=" * 72)

    candidates = [

        {
            "symbol": "NDAQ",
            "name": "Nasdaq, Inc.",
            "type": "Common Stock",
            "exchange": "NASDAQ",
            "country": "United States",
            "currency": "USD",
        },

        {
            "symbol": "TEST_NASDAQ",
            "name": "Nasdaq Composite Index",
            "type": "Index",
            "exchange": "TEST",
            "country": "United States",
            "currency": "USD",
        },

        {
            "symbol": "TEST_ETF",
            "name": "Nasdaq Composite ETF",
            "type": "ETF",
            "exchange": "TEST",
            "country": "United States",
            "currency": "USD",
        },

        {
            "symbol": "TEST_FOREIGN",
            "name": "Nasdaq Composite Index",
            "type": "Index",
            "exchange": "TEST",
            "country": "Germany",
            "currency": "EUR",
        },
    ]

    filtro = SymbolCandidateFilter()

    accepted = filtro.filter(
        "NASDAQ",
        candidates,
    )

    print()
    print(
        "CANDIDATOS ACEITOS"
    )
    print("-" * 72)

    for item in accepted:

        print(
            item
        )

    print()
    print(
        "CANDIDATOS REJEITADOS"
    )
    print("-" * 72)

    for item in filtro.rejected():

        print(
            item
        )

    assert (
        len(accepted)
        == 1
    )

    assert (
        accepted[0]["symbol"]
        == "TEST_NASDAQ"
    )

    assert (
        filtro.count()
        == 1
    )

    print()
    print(
        "SNAPSHOT"
    )
    print("-" * 72)

    print(
        filtro.snapshot()
    )

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL CANDIDATE FILTER "
        "RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()