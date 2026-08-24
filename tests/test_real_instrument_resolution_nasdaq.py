from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)

from external_context.providers.instrument_resolution_investigator import (
    InstrumentResolutionInvestigator,
)


def main():

    print()
    print("=" * 72)
    print(
        "TESTE REAL INSTRUMENT RESOLUTION "
        "NASDAQ RC2.3"
    )
    print("=" * 72)

    discovery = (
        TwelveDataSymbolDiscovery()
    )

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    result = investigator.investigate(
        "NASDAQ"
    )

    print()
    print(
        "INVESTIGAÇÃO"
    )
    print("-" * 72)

    print(
        result
    )

    print()
    print(
        "INDEX CANDIDATES"
    )
    print("-" * 72)

    for candidate in result[
        "index_candidates"
    ]:

        print(
            candidate
        )

    print()
    print(
        "=" * 72
    )
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "STATUS           :",
        result["status"],
    )

    print(
        "CANDIDATOS       :",
        result["candidate_count"],
    )

    print(
        "INVESTIGADOS     :",
        result["investigated_count"],
    )

    print(
        "INDEX CANDIDATES :",
        len(
            result[
                "index_candidates"
            ]
        ),
    )

    print()

    if result[
        "index_candidates"
    ]:

        print(
            "🟢 CANDIDATO INDEX "
            "ENCONTRADO"
        )

    elif result[
        "status"
    ] == "UNAVAILABLE":

        print(
            "⚠️ RECURSO "
            "INDISPONÍVEL"
        )

    elif result[
        "status"
    ] == "PROVIDER_ERROR":

        print(
            "⚠️ ERRO DO PROVIDER"
        )

    else:

        print(
            "⚠️ NENHUM INDEX "
            "COMPATÍVEL ENCONTRADO"
        )


if __name__ == "__main__":

    main()