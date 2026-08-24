"""
tests/test_provider_symbol_map_rc21.py

Teste offline do ProviderSymbolMap RC2.1.

Não utiliza API.
Não consome créditos.
"""

from external_context.providers.provider_symbol_map import (
    ProviderSymbolMap,
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


def teste_mapped():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: MAPPED"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = symbol_map.process(
        internal_asset="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        status="MAPPED",
    )

    print()
    print(
        f"resultado : {resultado}"
    )

    print(
        f"symbol    : "
        f"{symbol_map.get_symbol('NASDAQ')}"
    )

    print(
        f"status    : "
        f"{symbol_map.get_status('NASDAQ')}"
    )

    assert resultado is True

    assert (
        symbol_map.get_symbol(
            "NASDAQ"
        )
        == "TEST_NASDAQ"
    )

    assert (
        symbol_map.get_status(
            "NASDAQ"
        )
        == "MAPPED"
    )

    assert (
        symbol_map.has_symbol(
            "NASDAQ"
        )
        is True
    )

    assert (
        symbol_map.count()
        == 1
    )

    print(
        "✅ MAPPED APROVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "UNAVAILABLE"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = symbol_map.process(
        internal_asset="US500",
        provider_symbol="SPX",
        status="UNAVAILABLE",
        reason=(
            "S&P 500 disponível somente "
            "em plano Grow/Venture."
        ),
        metadata={
            "candidate": "SPX",
            "type": "Index",
        },
    )

    print()
    print(
        f"resultado : {resultado}"
    )

    print(
        f"symbol    : "
        f"{symbol_map.get_symbol('US500')}"
    )

    print(
        f"status    : "
        f"{symbol_map.get_status('US500')}"
    )

    print(
        f"reason    : "
        f"{symbol_map.get_reason('US500')}"
    )

    print(
        f"metadata  : "
        f"{symbol_map.get_metadata('US500')}"
    )

    assert resultado is False

    assert (
        symbol_map.get_symbol(
            "US500"
        )
        is None
    )

    assert (
        symbol_map.has_symbol(
            "US500"
        )
        is False
    )

    assert (
        symbol_map.get_status(
            "US500"
        )
        == "UNAVAILABLE"
    )

    assert (
        "Grow/Venture"
        in symbol_map.get_reason(
            "US500"
        )
    )

    assert (
        "US500"
        in symbol_map.unavailable()
    )

    assert (
        symbol_map.count()
        == 0
    )

    print(
        "✅ UNAVAILABLE BLOQUEADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "NOT_FOUND"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = symbol_map.process(
        internal_asset="DXY",
        provider_symbol=None,
        status="NOT_FOUND",
        reason=(
            "Símbolo não encontrado."
        ),
    )

    assert resultado is False

    assert (
        symbol_map.get_symbol(
            "DXY"
        )
        is None
    )

    assert (
        symbol_map.get_status(
            "DXY"
        )
        == "NOT_FOUND"
    )

    print(
        "✅ NOT_FOUND BLOQUEADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "PROVIDER_ERROR"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = symbol_map.process(
        internal_asset="VIX",
        provider_symbol=None,
        status="PROVIDER_ERROR",
        reason=(
            "Limite de API atingido."
        ),
    )

    assert resultado is False

    assert (
        symbol_map.get_symbol(
            "VIX"
        )
        is None
    )

    assert (
        symbol_map.get_status(
            "VIX"
        )
        == "PROVIDER_ERROR"
    )

    assert (
        "VIX"
        in symbol_map.provider_errors()
    )

    print(
        "✅ PROVIDER_ERROR BLOQUEADO"
    )


def teste_mapped_sem_symbol():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "MAPPED SEM SYMBOL"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = symbol_map.process(
        internal_asset="OIL",
        provider_symbol=None,
        status="MAPPED",
    )

    print()
    print(
        f"resultado : {resultado}"
    )

    print(
        f"status    : "
        f"{symbol_map.get_status('OIL')}"
    )

    print(
        f"reason    : "
        f"{symbol_map.get_reason('OIL')}"
    )

    assert resultado is False

    assert (
        symbol_map.get_symbol(
            "OIL"
        )
        is None
    )

    assert (
        symbol_map.get_status(
            "OIL"
        )
        == "NOT_FOUND"
    )

    print(
        "✅ MAPPED SEM SYMBOL BLOQUEADO"
    )


def teste_missing_complete():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "MISSING / COMPLETE"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    symbol_map.set_symbol(
        "NASDAQ",
        "TEST_NASDAQ",
    )

    symbol_map.set_symbol(
        "DXY",
        "TEST_DXY",
    )

    print()
    print(
        f"count    : "
        f"{symbol_map.count()}"
    )

    print(
        f"missing  : "
        f"{symbol_map.missing(REQUIRED)}"
    )

    print(
        f"complete : "
        f"{symbol_map.is_complete(REQUIRED)}"
    )

    assert (
        symbol_map.count()
        == 2
    )

    assert (
        symbol_map.is_complete(
            REQUIRED
        )
        is False
    )

    assert (
        "US500"
        in symbol_map.missing(
            REQUIRED
        )
    )

    print(
        "✅ MISSING / COMPLETE APROVADO"
    )


def teste_snapshot():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "SNAPSHOT"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    symbol_map.process(
        internal_asset="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        status="MAPPED",
    )

    symbol_map.process(
        internal_asset="US500",
        provider_symbol="SPX",
        status="UNAVAILABLE",
        reason=(
            "Plano atual sem acesso."
        ),
    )

    snapshot = (
        symbol_map.snapshot()
    )

    print()

    for key, value in snapshot.items():

        print(
            f"{key:15}: {value}"
        )

    assert (
        snapshot["name"]
        == "ProviderSymbolMap"
    )

    assert (
        snapshot["version"]
        == "RC2.1"
    )

    assert (
        snapshot["provider"]
        == "TwelveData"
    )

    assert (
        snapshot["symbols"]["NASDAQ"]
        == "TEST_NASDAQ"
    )

    assert (
        "US500"
        not in snapshot["symbols"]
    )

    assert (
        snapshot["status"]["US500"]
        == "UNAVAILABLE"
    )

    assert (
        "US500"
        in snapshot["unavailable"]
    )

    print(
        "✅ SNAPSHOT APROVADO"
    )


def teste_clear():

    print()
    print("=" * 72)
    print(
        "TESTE PROVIDER SYMBOL MAP RC2.1: "
        "CLEAR"
    )
    print("=" * 72)

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    symbol_map.process(
        internal_asset="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        status="MAPPED",
    )

    symbol_map.process(
        internal_asset="US500",
        provider_symbol=None,
        status="UNAVAILABLE",
        reason="Plano sem acesso.",
    )

    print()
    print(
        f"ANTES"
    )

    print(
        f"symbols : "
        f"{symbol_map.all_symbols()}"
    )

    print(
        f"status  : "
        f"{symbol_map.all_status()}"
    )

    symbol_map.clear()

    print()
    print(
        "DEPOIS"
    )

    print(
        f"symbols : "
        f"{symbol_map.all_symbols()}"
    )

    print(
        f"status  : "
        f"{symbol_map.all_status()}"
    )

    assert (
        symbol_map.count()
        == 0
    )

    assert (
        symbol_map.all_symbols()
        == {}
    )

    assert (
        symbol_map.all_status()
        == {}
    )

    assert (
        symbol_map.all_reasons()
        == {}
    )

    print(
        "✅ CLEAR APROVADO"
    )


def main():

    teste_mapped()

    teste_unavailable()

    teste_not_found()

    teste_provider_error()

    teste_mapped_sem_symbol()

    teste_missing_complete()

    teste_snapshot()

    teste_clear()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 PROVIDER SYMBOL MAP "
        "RC2.1 APROVADO"
    )


if __name__ == "__main__":

    main()