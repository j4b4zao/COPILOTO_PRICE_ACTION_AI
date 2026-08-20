"""
tests/test_twelvedata_real_us500.py

Primeiro teste REAL da Twelve Data.

Objetivo:
- consultar o catálogo;
- pesquisar US500;
- mostrar todos os candidatos;
- NÃO escolher automaticamente nenhum símbolo.

RC1
"""

import os

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


def main():

    print()
    print("=" * 72)
    print("TESTE REAL TWELVE DATA: US500")
    print("=" * 72)

    api_key = os.getenv(
        "TWELVE_DATA_API_KEY"
    )

    if not api_key:

        print()
        print(
            "❌ API KEY NÃO ENCONTRADA"
        )

        return

    print()
    print("API KEY")
    print("-" * 72)

    print(
        "TWELVE_DATA_API_KEY : configurada"
    )

    discovery = (
        TwelveDataSymbolDiscovery(
            api_key=api_key,
            timeout=10.0,
        )
    )

    # ==========================================================
    # CONSULTA
    # ==========================================================

    print()
    print("CONSULTA")
    print("-" * 72)

    print(
        "query        : US500"
    )

    results = discovery.search(
        "US500"
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

    # ==========================================================
    # ERRO DO PROVIDER
    # ==========================================================

    if (
        discovery.last_status
        == discovery.STATUS_PROVIDER_ERROR
    ):

        print()
        print(
            "❌ PROVIDER ERROR"
        )

        print(
            "A consulta real não conseguiu "
            "ser concluída."
        )

        return

    # ==========================================================
    # NENHUM RESULTADO
    # ==========================================================

    if not results:

        print()
        print(
            "⚠️ NENHUM INSTRUMENTO ENCONTRADO"
        )

        print()
        print(
            "Não vamos criar um símbolo "
            "por suposição."
        )

        return

    # ==========================================================
    # RESULTADOS
    # ==========================================================

    print()
    print("CANDIDATOS ENCONTRADOS")
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

    # ==========================================================
    # IMPORTANTE
    # ==========================================================

    print()
    print("=" * 72)

    print(
        "⚠️ RESULTADO NÃO É AINDA UM MAPA VALIDADO"
    )

    print()
    print(
        "Os candidatos foram apenas descobertos."
    )

    print(
        "Nenhum símbolo foi selecionado automaticamente."
    )

    print()
    print(
        "Próximo passo:"
    )

    print(
        "validar qual instrumento representa "
        "corretamente o US500 para o projeto."
    )


if __name__ == "__main__":

    main()