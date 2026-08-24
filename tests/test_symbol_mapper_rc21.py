"""
tests/test_symbol_mapper_rc21.py

Testes offline do SymbolMapper RC2.1.

Não utiliza API.
Não consome créditos.
"""

from external_context.providers.symbol_mapper import (
    SymbolMapper,
)


SYMBOLS = [
    "US500",
    "NASDAQ",
    "DXY",
    "VIX",
    "US10Y",
    "OIL",
    "GOLD",
]


def teste_found():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL MAPPER RC2.1: FOUND"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        SYMBOLS
    )

    resultado = mapper.process_discovery(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
        reason="Símbolo encontrado.",
    )

    print()
    print(
        f"resultado : {resultado}"
    )

    print(
        f"mapping   : "
        f"{mapper.get('NASDAQ')}"
    )

    print(
        f"status    : "
        f"{mapper.get_status('NASDAQ')}"
    )

    assert resultado is True

    assert (
        mapper.get("NASDAQ")
        == "TEST_NASDAQ"
    )

    assert (
        mapper.get_status("NASDAQ")
        == "MAPPED"
    )

    print(
        "✅ FOUND APROVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL MAPPER RC2.1: "
        "UNAVAILABLE"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        SYMBOLS
    )

    resultado = mapper.process_discovery(
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason=(
            "S&P 500 disponível "
            "somente em plano Grow/Venture."
        ),
    )

    print()
    print(
        f"resultado : {resultado}"
    )

    print(
        f"mapping   : "
        f"{mapper.get('US500')}"
    )

    print(
        f"status    : "
        f"{mapper.get_status('US500')}"
    )

    print(
        f"reason    : "
        f"{mapper.get_reason('US500')}"
    )

    assert resultado is False

    assert (
        mapper.get("US500")
        is None
    )

    assert (
        mapper.get_status("US500")
        == "UNAVAILABLE"
    )

    assert (
        "Grow/Venture"
        in mapper.get_reason(
            "US500"
        )
    )

    print(
        "✅ UNAVAILABLE BLOQUEADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL MAPPER RC2.1: "
        "NOT_FOUND"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        SYMBOLS
    )

    resultado = mapper.process_discovery(
        internal_symbol="DXY",
        provider_symbol=None,
        discovery_status="NOT_FOUND",
        reason=(
            "Símbolo não encontrado."
        ),
    )

    assert resultado is False

    assert (
        mapper.get("DXY")
        is None
    )

    assert (
        mapper.get_status("DXY")
        == "NOT_FOUND"
    )

    print(
        "✅ NOT_FOUND BLOQUEADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL MAPPER RC2.1: "
        "PROVIDER_ERROR"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        SYMBOLS
    )

    resultado = mapper.process_discovery(
        internal_symbol="VIX",
        provider_symbol=None,
        discovery_status="PROVIDER_ERROR",
        reason=(
            "Erro de comunicação."
        ),
    )

    assert resultado is False

    assert (
        mapper.get("VIX")
        is None
    )

    assert (
        mapper.get_status("VIX")
        == "PROVIDER_ERROR"
    )

    print(
        "✅ PROVIDER_ERROR BLOQUEADO"
    )


def teste_incomplete():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL MAPPER RC2.1: "
        "MAPA INCOMPLETO"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        SYMBOLS
    )

    mapper.process_discovery(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
    )

    mapper.process_discovery(
        internal_symbol="DXY",
        provider_symbol="TEST_DXY",
        discovery_status="FOUND",
    )

    print()
    print(
        f"count    : {mapper.count()}"
    )

    print(
        f"missing  : {mapper.missing()}"
    )

    print(
        f"complete : {mapper.is_complete()}"
    )

    assert (
        mapper.count()
        == 2
    )

    assert (
        mapper.is_complete()
        is False
    )

    assert (
        "US500"
        in mapper.missing()
    )

    print(
        "✅ MAPA INCOMPLETO DETECTADO"
    )


def teste_snapshot():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL MAPPER RC2.1: "
        "SNAPSHOT"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        SYMBOLS
    )

    mapper.process_discovery(
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
    )

    mapper.process_discovery(
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason=(
            "Plano atual sem acesso."
        ),
    )

    snapshot = mapper.snapshot()

    print()

    for key, value in snapshot.items():

        print(
            f"{key:15}: {value}"
        )

    assert (
        snapshot["version"]
        == "RC2.1"
    )

    assert (
        snapshot["mapping"]["NASDAQ"]
        == "TEST_NASDAQ"
    )

    assert (
        snapshot["mapping"]["US500"]
        is None
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


def main():

    teste_found()

    teste_unavailable()

    teste_not_found()

    teste_provider_error()

    teste_incomplete()

    teste_snapshot()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL MAPPER RC2.1 APROVADO"
    )


if __name__ == "__main__":

    main()