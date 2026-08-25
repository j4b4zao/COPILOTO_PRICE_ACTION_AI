"""Teste offline de mapa incompleto do SymbolMapper RC2.1."""

from external_context.providers.symbol_map import ExternalSymbolMap
from external_context.providers.symbol_mapper import SymbolMapper


EXPECTED_PRESENT = {
    "US500": "TEST_US500",
    "NASDAQ": "TEST_NASDAQ",
    "DXY": "TEST_DXY",
    "VIX": "TEST_VIX",
    "OIL": "TEST_OIL",
    "GOLD": "TEST_GOLD",
}


def main():
    print()
    print("=" * 72)
    print("TESTE SYMBOL MAPPER RC2.1: MAPA INCOMPLETO")
    print("=" * 72)

    mapper = SymbolMapper(ExternalSymbolMap.ALL)
    mapper.process_many(
        [
            {
                "internal_symbol": asset,
                "provider_symbol": provider_symbol,
                "status": "FOUND",
            }
            for asset, provider_symbol in EXPECTED_PRESENT.items()
        ]
        + [
            {
                "internal_symbol": "US10Y",
                "provider_symbol": None,
                "status": "NOT_FOUND",
                "reason": "Ativo ausente no provider controlado.",
            }
        ]
    )

    for asset in ExternalSymbolMap.ALL:
        print(f"{asset:<10} : {mapper.get(asset)}")

    print()
    print(f"COUNT        : {mapper.count()}")
    print(f"COMPLETE     : {mapper.is_complete()}")
    print(f"MISSING      : {mapper.missing()}")

    assert mapper.count() == len(EXPECTED_PRESENT)
    assert mapper.is_complete() is False
    assert mapper.missing() == ["US10Y"]

    for asset, expected_symbol in EXPECTED_PRESENT.items():
        assert mapper.get(asset) == expected_symbol
        assert mapper.get_status(asset) == "MAPPED"

    assert mapper.get("US10Y") is None
    assert mapper.get_status("US10Y") == "NOT_FOUND"

    print()
    print("✅ MAPA INCOMPLETO DETECTADO CORRETAMENTE")


if __name__ == "__main__":
    main()
