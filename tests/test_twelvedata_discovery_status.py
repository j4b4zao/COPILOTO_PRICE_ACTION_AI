"""
tests/test_twelvedata_discovery_status.py

Teste offline dos estados do
TwelveDataSymbolDiscovery.

RC2.1

Não utiliza API.
Não consome créditos.
"""

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


def verificar(
    esperado: str,
    status_code: int | None,
    message: str,
):

    resultado = (
        TwelveDataSymbolDiscovery
        .classify_provider_error(
            status_code,
            message,
        )
    )

    print()
    print(
        f"ESPERADO : {esperado}"
    )

    print(
        f"OBTIDO   : {resultado}"
    )

    if resultado != esperado:

        print(
            "❌ FALHOU"
        )

        return False

    print(
        "✅ PASSOU"
    )

    return True


def main():

    print()
    print("=" * 72)
    print(
        "TESTE TWELVE DATA DISCOVERY "
        "STATUS RC2.1"
    )
    print("=" * 72)

    resultados = []

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "TESTE: RECURSO DISPONÍVEL "
        "SOMENTE EM PLANO SUPERIOR"
    )
    print("=" * 72)

    resultados.append(
        verificar(
            "UNAVAILABLE",
            404,
            (
                "This symbol is available "
                "starting with the Grow or "
                "Venture plan."
            ),
        )
    )

    # ==========================================================
    # UNAVAILABLE - UPGRADE
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "TESTE: UPGRADE"
    )
    print("=" * 72)

    resultados.append(
        verificar(
            "UNAVAILABLE",
            403,
            (
                "Consider upgrading "
                "your plan."
            ),
        )
    )

    # ==========================================================
    # PROVIDER ERROR
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "TESTE: AUTENTICAÇÃO"
    )
    print("=" * 72)

    resultados.append(
        verificar(
            "PROVIDER_ERROR",
            401,
            (
                "apikey parameter is "
                "incorrect or not specified."
            ),
        )
    )

    # ==========================================================
    # RATE LIMIT
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "TESTE: RATE LIMIT"
    )
    print("=" * 72)

    resultados.append(
        verificar(
            "PROVIDER_ERROR",
            429,
            (
                "You have run out of "
                "API credits."
            ),
        )
    )

    # ==========================================================
    # OUTRO ERRO
    # ==========================================================

    print()
    print("=" * 72)
    print(
        "TESTE: ERRO DESCONHECIDO"
    )
    print("=" * 72)

    resultados.append(
        verificar(
            "PROVIDER_ERROR",
            500,
            "Internal Server Error",
        )
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

    if all(resultados):

        print()
        print(
            "🏆 TWELVE DATA DISCOVERY "
            "STATUS RC2.1 APROVADO"
        )

        return

    print()
    print(
        "❌ TWELVE DATA DISCOVERY "
        "STATUS RC2.1 FALHOU"
    )


if __name__ == "__main__":

    main()