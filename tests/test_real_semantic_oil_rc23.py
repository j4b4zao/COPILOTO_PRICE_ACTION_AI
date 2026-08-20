"""
tests/test_real_semantic_oil_rc23.py

Teste REAL da descoberta semântica do OIL.

RC2.3

Fluxo:

Instrument Profile
        ↓
InstrumentResolutionInvestigator
        ↓
TwelveDataSymbolDiscovery
        ↓
candidatos reais
        ↓
classificação dos instrumentos

IMPORTANTE:
Este teste NÃO grava mapa.
Este teste NÃO seleciona símbolo automaticamente.
"""

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)

from external_context.providers.instrument_resolution_investigator import (
    InstrumentResolutionInvestigator,
)


def main():

    print()
    print("=" * 72)
    print("TESTE REAL SEMANTIC OIL RC2.3")
    print("=" * 72)

    discovery = TwelveDataSymbolDiscovery()

    investigator = (
        InstrumentResolutionInvestigator(
            discovery
        )
    )

    print()
    print("CONFIGURAÇÃO")
    print("-" * 72)

    print(
        "internal_symbol : OIL"
    )

    print(
        "queries          : "
        "Crude Oil / WTI Crude Oil"
    )

    print(
        "allowed_types    : Commodity"
    )

    print(
        "allowed_country  : United States"
    )

    # ==========================================================
    # INVESTIGAÇÃO
    # ==========================================================

    print()
    print("=" * 72)
    print("INVESTIGAÇÃO REAL")
    print("=" * 72)

    result = investigator.investigate(
        "OIL",
        query="WTI Crude Oil",
    )

    print()
    print("RESULTADO")
    print("-" * 72)

    print(
        "status             :",
        result.get("status"),
    )

    print(
        "error              :",
        result.get("error"),
    )

    print(
        "query              :",
        result.get("query"),
    )

    print(
        "candidate_count    :",
        result.get("candidate_count"),
    )

    print(
        "investigated_count :",
        result.get("investigated_count"),
    )

    print(
        "index_candidates   :",
        result.get("index_candidates"),
    )

    print()
    print("CANDIDATOS INVESTIGADOS")
    print("-" * 72)

    for candidate in result.get(
        "investigated",
        [],
    ):

        print(candidate)

    # ==========================================================
    # CANDIDATOS POTENCIAIS
    # ==========================================================

    print()
    print("=" * 72)
    print("CANDIDATOS POTENCIAIS")
    print("=" * 72)

    potential = []

    for candidate in result.get(
        "investigated",
        [],
    ):

        if (
            candidate.get(
                "type"
            )
            == "Commodity"
            and candidate.get(
                "country"
            )
            == "United States"
        ):

            potential.append(
                candidate
            )

    print()
    print(
        "COUNT :",
        len(potential),
    )

    for candidate in potential:

        print(candidate)

    # ==========================================================
    # RESULTADO
    # ==========================================================

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print()
    print(
        "STATUS           :",
        result.get("status"),
    )

    print(
        "CANDIDATOS       :",
        result.get("candidate_count"),
    )

    print(
        "INVESTIGADOS     :",
        result.get("investigated_count"),
    )

    print(
        "POTENCIAIS OIL   :",
        len(potential),
    )

    print()

    if potential:

        print(
            "✅ CANDIDATO(S) COMPATÍVEL(IS) "
            "ENCONTRADO(S)"
        )

        print()
        print(
            "⚠️ NENHUM SÍMBOLO SERÁ "
            "SELECIONADO AUTOMATICAMENTE."
        )

    elif result.get(
        "status"
    ) == "UNAVAILABLE":

        print(
            "⚠️ OIL INDISPONÍVEL NO "
            "PLANO ATUAL."
        )

    elif result.get(
        "status"
    ) == "PROVIDER_ERROR":

        print(
            "❌ ERRO DO PROVIDER."
        )

        print(
            "ERROR :",
            result.get("error"),
        )

    elif result.get(
        "status"
    ) == "NOT_FOUND":

        print(
            "⚠️ NENHUM CANDIDATO "
            "ENCONTRADO."
        )

    else:

        print(
            "⚠️ NENHUM CANDIDATO "
            "COMPATÍVEL ENCONTRADO."
        )


if __name__ == "__main__":

    main()