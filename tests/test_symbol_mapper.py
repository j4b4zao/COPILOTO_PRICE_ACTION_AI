"""Teste offline do contrato atual do SymbolMapper RC2.1."""

from external_context.providers.symbol_map import ExternalSymbolMap
from external_context.providers.symbol_mapper import SymbolMapper


EXPECTED = {
    "US500": "TEST_US500",
    "NASDAQ": "TEST_NASDAQ",
    "DXY": "TEST_DXY",
    "VIX": "TEST_VIX",
    "US10Y": "TEST_US10Y",
    "OIL": "TEST_OIL",
    "GOLD": "TEST_GOLD",
}


def main():
    print()
    print("=" * 72)
    print("TESTE SYMBOL MAPPER RC2.1: MAPA COMPLETO")
    print("=" * 72)

    mapper = SymbolMapper(ExternalSymbolMap.ALL)
    mapper.process_many(
        [
            {
                "internal_symbol": asset,
                "provider_symbol": provider_symbol,
                "status": "FOUND",
                "reason": "Símbolo encontrado pelo provider controlado.",
            }
            for asset, provider_symbol in EXPECTED.items()
        ]
    )

    for asset in ExternalSymbolMap.ALL:
        print(f"{asset:<10} : {mapper.get(asset)}")

    print()
    print(f"COUNT        : {mapper.count()}")
    print(f"COMPLETE     : {mapper.is_complete()}")
    print(f"MISSING      : {mapper.missing()}")

    assert mapper.count() == len(EXPECTED)
    assert mapper.is_complete() is True
    assert mapper.missing() == []

    for asset, expected_symbol in EXPECTED.items():
        assert mapper.get(asset) == expected_symbol
        assert mapper.get_status(asset) == "MAPPED"

    print()
    print("✅ SYMBOL MAPPER RC2.1 APROVADO")


if __name__ == "__main__":
    main()
