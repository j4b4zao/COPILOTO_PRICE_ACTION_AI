"""
tests/test_twelvedata_real_spx.py

Discovery real do S&P 500 através de SPX.

RC2
"""

import os

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


def main():

    print()
    print("=" * 72)
    print("TESTE REAL TWELVE DATA: SPX")
    print("=" * 72)

    api_key = os.getenv(
        "TWELVE_DATA_API_KEY"
    )

    if not api_key:

        print(
            "❌ API KEY NÃO ENCONTRADA"
        )

        return

    discovery = (
        TwelveDataSymbolDiscovery(
            api_key=api_key,
            timeout=10.0,
        )
    )

    print()
    print("CONSULTA")
    print("-" * 72)

    print(
        "query        : SPX"
    )

    results = discovery.search(
        "SPX"
    )

    print(
        f"status       : "
        f"{discovery.last_status}"
    )

    print(
        f"error        : "
        f"{discovery.last_error}"
    )

    print(
        f"resultados   : "
        f"{len(results)}"
    )

    if (
        discovery.last_status
        == discovery.STATUS_PROVIDER_ERROR
    ):

        print()
        print(
            "❌ PROVIDER ERROR"
        )

        return

    print()
    print("CANDIDATOS")
    print("-" * 72)

    for index, result in enumerate(
        results,
        start=1,
    ):

        print()
        print(
            f"[{index}]"
        )

        print(
            f"symbol       : "
            f"{result.get('symbol', '')}"
        )

        print(
            f"name         : "
            f"{result.get('name', '')}"
        )

        print(
            f"type         : "
            f"{result.get('type', '')}"
        )

        print(
            f"exchange     : "
            f"{result.get('exchange', '')}"
        )

        print(
            f"mic_code     : "
            f"{result.get('mic_code', '')}"
        )

        print(
            f"country      : "
            f"{result.get('country', '')}"
        )

        print(
            f"currency     : "
            f"{result.get('currency', '')}"
        )

    print()
    print("=" * 72)

    if not results:

        print(
            "⚠️ Nenhum candidato encontrado."
        )

        return

    print(
        "✅ CANDIDATOS SPX ENCONTRADOS"
    )

    print()
    print(
        "⚠️ Nenhum símbolo será "
        "selecionado automaticamente."
    )


if __name__ == "__main__":

    main()