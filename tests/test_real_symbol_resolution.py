"""
tests/test_real_symbol_resolution.py

Primeiro teste REAL do fluxo:

Twelve Data
    ↓
Discovery
    ↓
Resolution Provider
    ↓
Resolution Engine
    ↓
Provider Symbol Map

RC2.1

ATENÇÃO:
Este teste faz UMA consulta real à Twelve Data.
"""

import os

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)

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


def main():

    print()
    print("=" * 72)
    print(
        "TESTE REAL SYMBOL RESOLUTION RC2.1"
    )
    print("=" * 72)

    api_key = os.getenv(
        "TWELVE_DATA_API_KEY",
        "",
    ).strip()

    print()
    print(
        "API KEY"
    )
    print("-" * 72)

    print(
        "TWELVE_DATA_API_KEY : "
        f"{'configurada' if api_key else 'NÃO configurada'}"
    )

    if not api_key:

        print()
        print(
            "❌ API KEY NÃO CONFIGURADA"
        )

        return

    # ==========================================================
    # DISCOVERY
    # ==========================================================

    discovery = (
        TwelveDataSymbolDiscovery(
            api_key=api_key
        )
    )

    # ==========================================================
    # ENGINE
    # ==========================================================

    engine = SymbolResolutionEngine(
        provider_name="TwelveData",
        required_symbols=REQUIRED,
    )

    # ==========================================================
    # PROVIDER
    # ==========================================================

    provider = (
        SymbolResolutionProvider(
            discovery=discovery,
            engine=engine,
        )
    )

    # ==========================================================
    # UMA ÚNICA CONSULTA
    # ==========================================================

    internal_symbol = "NASDAQ"

    query = "NASDAQ"

    print()
    print("=" * 72)
    print(
        "CONSULTA REAL"
    )
    print("=" * 72)

    print()
    print(
        f"internal : {internal_symbol}"
    )

    print(
        f"query    : {query}"
    )

    result = provider.resolve(
        internal_symbol=internal_symbol,
        query=query,
    )

    # ==========================================================
    # DISCOVERY
    # ==========================================================

    print()
    print(
        "DISCOVERY"
    )
    print("-" * 72)

    print(
        f"status   : "
        f"{discovery.last_status}"
    )

    print(
        f"error    : "
        f"{discovery.last_error}"
    )

    # ==========================================================
    # RESULTADO
    # ==========================================================

    print()
    print(
        "RESOLUTION RESULT"
    )
    print("-" * 72)

    print(
        f"internal : "
        f"{result.internal_symbol}"
    )

    print(
        f"candidate: "
        f"{result.candidate_symbol}"
    )

    print(
        f"mapped   : "
        f"{result.mapped_symbol}"
    )

    print(
        f"discovery: "
        f"{result.discovery_status}"
    )

    print(
        f"mapper   : "
        f"{result.mapper_status}"
    )

    print(
        f"final    : "
        f"{result.final_status}"
    )

    print(
        f"resolved : "
        f"{result.resolved}"
    )

    print(
        f"reason   : "
        f"{result.reason}"
    )

    print()
    print(
        "METADATA"
    )
    print("-" * 72)

    print(
        result.metadata
    )

    # ==========================================================
    # MAPA FINAL
    # ==========================================================

    print()
    print(
        "PROVIDER SYMBOL MAP"
    )
    print("-" * 72)

    print(
        engine.resolved_symbols()
    )

    print()
    print(
        f"count        : "
        f"{engine.count()}"
    )

    print(
        f"missing      : "
        f"{engine.missing()}"
    )

    print(
        f"complete     : "
        f"{engine.is_complete()}"
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

    if result.resolved:

        print()
        print(
            "🟢 SYMBOL RESOLUTION REAL "
            "APROVADO"
        )

        print()
        print(
            "NASDAQ foi resolvido para:"
        )

        print(
            f"→ {result.mapped_symbol}"
        )

    elif result.final_status == "UNAVAILABLE":

        print()
        print(
            "⚠️ RECURSO INDISPONÍVEL"
        )

        print(
            "O provider encontrou o recurso, "
            "mas ele não está disponível "
            "para o plano/API atual."
        )

    elif result.final_status == "NOT_FOUND":

        print()
        print(
            "⚠️ SÍMBOLO NÃO RESOLVIDO"
        )

        print(
            "Nenhum candidato válido foi "
            "encontrado."
        )

    elif result.final_status == "PROVIDER_ERROR":

        print()
        print(
            "⚠️ ERRO DO PROVIDER"
        )

        print(
            result.reason
        )

    else:

        print()
        print(
            "⚠️ RESOLUÇÃO NÃO CONCLUÍDA"
        )


if __name__ == "__main__":

    main()