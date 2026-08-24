"""
Teste REAL da resolução semântica do NASDAQ.

RC2.3

Executa as queries definidas no InstrumentProfiles:

    Nasdaq Composite
    Nasdaq Composite Index

ATENÇÃO:
Este teste utiliza a API real da Twelve Data.
"""

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)

from external_context.providers.semantic_discovery_runner import (
    SemanticDiscoveryRunner,
)

from external_context.providers.semantic_symbol_resolution_pipeline import (
    SemanticSymbolResolutionPipeline,
)


def main():

    print()
    print("=" * 72)
    print(
        "TESTE REAL SEMANTIC NASDAQ RC2.3"
    )
    print("=" * 72)

    # ----------------------------------------------------------
    # DISCOVERY
    # ----------------------------------------------------------

    discovery = (
        TwelveDataSymbolDiscovery()
    )

    runner = (
        SemanticDiscoveryRunner(
            discovery
        )
    )

    print()
    print(
        "DISCOVERY SEMÂNTICO"
    )
    print("-" * 72)

    discovery_result = (
        runner.search(
            "NASDAQ"
        )
    )

    print(
        discovery_result
    )

    # ----------------------------------------------------------
    # BLOQUEIO DE ERROS
    # ----------------------------------------------------------

    if (
        discovery_result["status"]
        != "FOUND"
    ):

        print()
        print("=" * 72)
        print(
            "RESULTADO"
        )
        print("=" * 72)

        print()
        print(
            "⚠️ DISCOVERY NÃO RETORNOU "
            "CANDIDATOS RESOLVÍVEIS"
        )

        print(
            f"status : "
            f"{discovery_result['status']}"
        )

        print(
            f"error  : "
            f"{discovery_result['error']}"
        )

        return

    # ----------------------------------------------------------
    # SEMANTIC PIPELINE
    # ----------------------------------------------------------

    pipeline = (
        SemanticSymbolResolutionPipeline()
    )

    resolution = (
        pipeline.resolve(
            "NASDAQ",
            discovery_result[
                "results"
            ],
        )
    )

    print()
    print(
        "RESOLUÇÃO SEMÂNTICA"
    )
    print("-" * 72)

    print(
        resolution
    )

    # ----------------------------------------------------------
    # RESULTADO
    # ----------------------------------------------------------

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        f"STATUS     : "
        f"{resolution['status']}"
    )

    print(
        f"SYMBOL     : "
        f"{resolution['symbol']}"
    )

    print(
        f"CONFIDENCE : "
        f"{resolution['confidence']}"
    )

    print(
        f"RESOLVED   : "
        f"{resolution['resolved']}"
    )

    print()

    if resolution["resolved"]:

        print(
            "🏆 NASDAQ RESOLVIDO "
            "SEMANTICAMENTE"
        )

    else:

        print(
            "⚠️ NASDAQ NÃO RESOLVIDO"
        )

        print(
            "Nenhum símbolo será "
            "adicionado ao mapa."
        )


if __name__ == "__main__":

    main()