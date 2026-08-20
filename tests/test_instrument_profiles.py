from external_context.providers.instrument_profiles import (
    InstrumentProfiles,
)


def main():

    print()
    print("=" * 72)
    print(
        "TESTE INSTRUMENT PROFILES RC2.3"
    )
    print("=" * 72)

    symbols = [
        "NASDAQ",
        "US500",
        "DXY",
        "VIX",
        "US10Y",
        "OIL",
        "GOLD",
    ]

    for symbol in symbols:

        profile = (
            InstrumentProfiles.get(
                symbol
            )
        )

        print()
        print(symbol)
        print("-" * 72)

        print(
            f"queries          : "
            f"{profile['queries']}"
        )

        print(
            f"allowed_types    : "
            f"{profile['allowed_types']}"
        )

        print(
            f"allowed_countries: "
            f"{profile['allowed_countries']}"
        )

        print(
            f"name_keywords    : "
            f"{profile['name_keywords']}"
        )

        assert profile is not None

    print()
    print("=" * 72)

    print(
        "TESTE DESCONHECIDO"
    )

    assert (
        InstrumentProfiles.get(
            "BTCUSD"
        )
        is None
    )

    print(
        "BTCUSD : corretamente "
        "sem perfil"
    )

    print()
    print("=" * 72)
    print(
        "RESULTADO FINAL"
    )
    print("=" * 72)

    print()
    print(
        "🏆 INSTRUMENT PROFILES "
        "RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()