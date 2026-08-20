"""
tests/test_real_twelvedata_ixic.py

Teste real Twelve Data: IXIC
RC2.3
"""

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


def main():

    print()
    print("=" * 72)
    print("TESTE REAL TWELVE DATA: IXIC")
    print("=" * 72)

    discovery = TwelveDataSymbolDiscovery()

    print()
    print("DISCOVERY")
    print("-" * 72)

    results = discovery.search("IXIC")

    status = discovery.last_status
    error = discovery.last_error

    print()
    print("QUERY  : IXIC")
    print("STATUS :", status)
    print("ERROR  :", error)
    print("COUNT  :", len(results))

    print()
    print("CANDIDATOS")
    print("-" * 72)

    for candidate in results:

        print(candidate)

    print()
    print("=" * 72)
    print("RESULTADO")
    print("=" * 72)

    if status == "FOUND":

        print()
        print("✅ CONSULTA IXIC RETORNOU CANDIDATOS")

    elif status == "NOT_FOUND":

        print()
        print("⚠️ IXIC NÃO ENCONTRADO")

    elif status == "UNAVAILABLE":

        print()
        print("⚠️ IXIC INDISPONÍVEL NO PLANO")

    elif status == "PROVIDER_ERROR":

        print()
        print("❌ ERRO DO PROVIDER")

        if error:
            print(
                f"ERRO     : {error}"
            )

    else:

        print()
        print(
            "⚠️ STATUS NÃO ESPERADO:",
            status,
        )


if __name__ == "__main__":

    main()