"""
tests/test_symbol_resolution_pipeline_rc21.py

Integração offline:

TwelveDataSymbolDiscovery
        ↓
SymbolMapper
        ↓
ProviderSymbolMap

RC2.1

Não utiliza API.
Não consome créditos.
"""

from external_context.providers.symbol_mapper import (
    SymbolMapper,
)

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


def resolver(
    mapper: SymbolMapper,
    symbol_map: ProviderSymbolMap,
    *,
    internal_symbol: str,
    provider_symbol: str | None,
    discovery_status: str,
    reason: str = "",
    metadata: dict | None = None,
) -> bool:
    """
    Executa:

    Discovery result
        ↓
    SymbolMapper
        ↓
    ProviderSymbolMap
    """

    mapper_result = mapper.process_discovery(
        internal_symbol=internal_symbol,
        provider_symbol=provider_symbol,
        discovery_status=discovery_status,
        reason=reason,
        metadata=metadata,
    )

    mapper_status = mapper.get_status(
        internal_symbol
    )

    mapper_reason = mapper.get_reason(
        internal_symbol
    )

    mapped_symbol = mapper.get(
        internal_symbol
    )

    # ----------------------------------------------------------
    # MAPPER → PROVIDER SYMBOL MAP
    # ----------------------------------------------------------

    if mapper_result:

        symbol_map.process(
            internal_asset=internal_symbol,
            provider_symbol=mapped_symbol,
            status="MAPPED",
            reason=mapper_reason,
            metadata=metadata,
        )

    else:

        symbol_map.process(
            internal_asset=internal_symbol,
            provider_symbol=provider_symbol,
            status=mapper_status,
            reason=mapper_reason,
            metadata=metadata,
        )

    return mapper_result


def teste_found():

    print()
    print("=" * 72)
    print(
        "TESTE RESOLUTION: FOUND → MAPPED"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        REQUIRED
    )

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = resolver(
        mapper,
        symbol_map,
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
        reason="Símbolo validado.",
        metadata={
            "type": "Index",
            "country": "United States",
        },
    )

    print()
    print(
        "MAPPER"
    )
    print("-" * 72)

    print(
        f"result     : {resultado}"
    )

    print(
        f"status     : "
        f"{mapper.get_status('NASDAQ')}"
    )

    print(
        f"symbol     : "
        f"{mapper.get('NASDAQ')}"
    )

    print()
    print(
        "PROVIDER SYMBOL MAP"
    )
    print("-" * 72)

    print(
        f"status     : "
        f"{symbol_map.get_status('NASDAQ')}"
    )

    print(
        f"symbol     : "
        f"{symbol_map.get_symbol('NASDAQ')}"
    )

    assert resultado is True

    assert (
        mapper.get("NASDAQ")
        == "TEST_NASDAQ"
    )

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

    print()
    print(
        "✅ FOUND → MAPPED APROVADO"
    )


def teste_unavailable():

    print()
    print("=" * 72)
    print(
        "TESTE RESOLUTION: "
        "UNAVAILABLE → BLOQUEADO"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        REQUIRED
    )

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = resolver(
        mapper,
        symbol_map,
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason=(
            "S&P 500 disponível somente "
            "em plano Grow/Venture."
        ),
        metadata={
            "candidate": "SPX",
            "type": "Index",
            "country": "United States",
        },
    )

    print()
    print(
        "MAPPER"
    )
    print("-" * 72)

    print(
        f"result     : {resultado}"
    )

    print(
        f"status     : "
        f"{mapper.get_status('US500')}"
    )

    print(
        f"symbol     : "
        f"{mapper.get('US500')}"
    )

    print()
    print(
        "PROVIDER SYMBOL MAP"
    )
    print("-" * 72)

    print(
        f"status     : "
        f"{symbol_map.get_status('US500')}"
    )

    print(
        f"symbol     : "
        f"{symbol_map.get_symbol('US500')}"
    )

    print(
        f"reason     : "
        f"{symbol_map.get_reason('US500')}"
    )

    assert resultado is False

    assert (
        mapper.get("US500")
        is None
    )

    assert (
        symbol_map.get_symbol(
            "US500"
        )
        is None
    )

    assert (
        symbol_map.get_status(
            "US500"
        )
        == "UNAVAILABLE"
    )

    assert (
        "US500"
        in symbol_map.unavailable()
    )

    print()
    print(
        "✅ UNAVAILABLE → BLOQUEADO APROVADO"
    )


def teste_not_found():

    print()
    print("=" * 72)
    print(
        "TESTE RESOLUTION: "
        "NOT_FOUND → BLOQUEADO"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        REQUIRED
    )

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = resolver(
        mapper,
        symbol_map,
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
        symbol_map.get_symbol("DXY")
        is None
    )

    assert (
        symbol_map.get_status("DXY")
        == "NOT_FOUND"
    )

    print(
        "✅ NOT_FOUND → BLOQUEADO APROVADO"
    )


def teste_provider_error():

    print()
    print("=" * 72)
    print(
        "TESTE RESOLUTION: "
        "PROVIDER_ERROR → BLOQUEADO"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        REQUIRED
    )

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resultado = resolver(
        mapper,
        symbol_map,
        internal_symbol="VIX",
        provider_symbol=None,
        discovery_status="PROVIDER_ERROR",
        reason=(
            "Provider indisponível."
        ),
    )

    assert resultado is False

    assert (
        mapper.get("VIX")
        is None
    )

    assert (
        symbol_map.get_symbol("VIX")
        is None
    )

    assert (
        symbol_map.get_status("VIX")
        == "PROVIDER_ERROR"
    )

    assert (
        "VIX"
        in symbol_map.provider_errors()
    )

    print(
        "✅ PROVIDER_ERROR → "
        "BLOQUEADO APROVADO"
    )


def teste_mixed_pipeline():

    print()
    print("=" * 72)
    print(
        "TESTE RESOLUTION: "
        "CENÁRIO MISTO"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        REQUIRED
    )

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    # ----------------------------------------------------------
    # VALID
    # ----------------------------------------------------------

    resolver(
        mapper,
        symbol_map,
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
    )

    # ----------------------------------------------------------
    # UNAVAILABLE
    # ----------------------------------------------------------

    resolver(
        mapper,
        symbol_map,
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason=(
            "Plano atual sem acesso."
        ),
    )

    # ----------------------------------------------------------
    # NOT FOUND
    # ----------------------------------------------------------

    resolver(
        mapper,
        symbol_map,
        internal_symbol="DXY",
        provider_symbol=None,
        discovery_status="NOT_FOUND",
        reason=(
            "Símbolo não encontrado."
        ),
    )

    # ----------------------------------------------------------
    # PROVIDER ERROR
    # ----------------------------------------------------------

    resolver(
        mapper,
        symbol_map,
        internal_symbol="VIX",
        provider_symbol=None,
        discovery_status="PROVIDER_ERROR",
        reason=(
            "Provider indisponível."
        ),
    )

    print()
    print(
        "MAPA FINAL"
    )
    print("-" * 72)

    print(
        f"symbols        : "
        f"{symbol_map.all_symbols()}"
    )

    print(
        f"status         : "
        f"{symbol_map.all_status()}"
    )

    print(
        f"unavailable    : "
        f"{symbol_map.unavailable()}"
    )

    print(
        f"provider_errors: "
        f"{symbol_map.provider_errors()}"
    )

    print(
        f"count          : "
        f"{symbol_map.count()}"
    )

    print(
        f"missing        : "
        f"{symbol_map.missing(REQUIRED)}"
    )

    # ----------------------------------------------------------
    # VALIDAÇÕES
    # ----------------------------------------------------------

    assert (
        symbol_map.get_symbol(
            "NASDAQ"
        )
        == "TEST_NASDAQ"
    )

    assert (
        symbol_map.get_symbol(
            "US500"
        )
        is None
    )

    assert (
        symbol_map.get_symbol(
            "DXY"
        )
        is None
    )

    assert (
        symbol_map.get_symbol(
            "VIX"
        )
        is None
    )

    assert (
        symbol_map.get_status(
            "US500"
        )
        == "UNAVAILABLE"
    )

    assert (
        symbol_map.get_status(
            "DXY"
        )
        == "NOT_FOUND"
    )

    assert (
        symbol_map.get_status(
            "VIX"
        )
        == "PROVIDER_ERROR"
    )

    assert (
        symbol_map.count()
        == 1
    )

    assert (
        symbol_map.is_complete(
            REQUIRED
        )
        is False
    )

    print()
    print(
        "✅ CENÁRIO MISTO APROVADO"
    )


def teste_clear_pipeline():

    print()
    print("=" * 72)
    print(
        "TESTE RESOLUTION: CLEAR"
    )
    print("=" * 72)

    mapper = SymbolMapper(
        REQUIRED
    )

    symbol_map = ProviderSymbolMap(
        "TwelveData"
    )

    resolver(
        mapper,
        symbol_map,
        internal_symbol="NASDAQ",
        provider_symbol="TEST_NASDAQ",
        discovery_status="FOUND",
    )

    resolver(
        mapper,
        symbol_map,
        internal_symbol="US500",
        provider_symbol="SPX",
        discovery_status="UNAVAILABLE",
        reason="Plano sem acesso.",
    )

    assert (
        symbol_map.count()
        == 1
    )

    assert (
        symbol_map.unavailable()
        == ["US500"]
    )

    symbol_map.clear()

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
        "✅ CLEAR PIPELINE APROVADO"
    )


def main():

    print()
    print("=" * 72)
    print(
        "TESTE SYMBOL RESOLUTION "
        "PIPELINE RC2.1"
    )
    print("=" * 72)

    teste_found()

    teste_unavailable()

    teste_not_found()

    teste_provider_error()

    teste_mixed_pipeline()

    teste_clear_pipeline()

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 SYMBOL RESOLUTION "
        "PIPELINE RC2.1 APROVADO"
    )


if __name__ == "__main__":

    main()