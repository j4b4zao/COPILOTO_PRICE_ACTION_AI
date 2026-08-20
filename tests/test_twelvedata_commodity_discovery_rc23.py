"""
tests/test_twelvedata_commodity_discovery_rc23.py

Teste unitário/integração da camada:

TwelveDataCommodityDiscovery RC2.3
"""

from external_context.providers.twelvedata_commodity_discovery import (
    TwelveDataCommodityDiscovery,
)


def fake_provider_data():

    return [
        {
            "symbol": "URALS/USD",
            "name": "Urals Crude Oil Spot",
            "category": "Energy Resource",
            "description": "",
        },
        {
            "symbol": "WTI/USD",
            "name": "Crude Oil WTI Spot",
            "category": "Energy Resource",
            "description": "",
        },
        {
            "symbol": "XAU/USD",
            "name": "Gold Spot",
            "category": "Precious Metal",
            "description": "",
        },
        {
            "symbol": "OIL",
            "name": "Onyx Spot Return Crude Oil",
            "category": "ETF",
            "description": "",
        },
    ]


def main():

    print()
    print("=" * 72)
    print("TESTE TWELVE DATA COMMODITY DISCOVERY RC2.3")
    print("=" * 72)

    discovery = (
        TwelveDataCommodityDiscovery()
    )

    # ==========================================================
    # OIL
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: OIL")
    print("=" * 72)

    candidates = fake_provider_data()

    oil = [
        item
        for item in candidates
        if discovery._matches_profile(
            "OIL",
            item,
        )
    ]

    print()
    print(
        "CANDIDATOS :",
        oil,
    )

    assert len(oil) == 1
    assert oil[0]["symbol"] == "WTI/USD"

    print(
        "✅ OIL → WTI/USD APROVADO"
    )

    # ==========================================================
    # GOLD
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: GOLD")
    print("=" * 72)

    gold = [
        item
        for item in candidates
        if discovery._matches_profile(
            "GOLD",
            item,
        )
    ]

    print()
    print(
        "CANDIDATOS :",
        gold,
    )

    assert len(gold) == 1
    assert gold[0]["symbol"] == "XAU/USD"

    print(
        "✅ GOLD → XAU/USD APROVADO"
    )

    # ==========================================================
    # URALS NÃO É WTI
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: URALS NÃO É OIL")
    print("=" * 72)

    urals = candidates[0]

    assert not discovery._matches_profile(
        "OIL",
        urals,
    )

    print(
        "✅ URALS/USD BLOQUEADO"
    )

    # ==========================================================
    # ETF NÃO É COMMODITY
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: ETF NÃO É COMMODITY")
    print("=" * 72)

    etf = candidates[3]

    assert not discovery._matches_profile(
        "OIL",
        etf,
    )

    print(
        "✅ ETF OIL BLOQUEADO"
    )

    # ==========================================================
    # PERFIL DESCONHECIDO
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: PERFIL DESCONHECIDO")
    print("=" * 72)

    assert (
        discovery.profile(
            "BTCUSD"
        )
        is None
    )

    print(
        "✅ BTCUSD SEM PERFIL"
    )

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: CLEAR")
    print("=" * 72)

    discovery.last_status = "FOUND"
    discovery.last_error = "teste"
    discovery.last_query = "OIL"
    discovery.last_results = candidates

    discovery.clear()

    assert (
        discovery.last_status
        == ""
    )

    assert (
        discovery.last_error
        == ""
    )

    assert (
        discovery.last_query
        == ""
    )

    assert (
        discovery.last_results
        == []
    )

    print(
        "✅ CLEAR APROVADO"
    )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    print()
    print("=" * 72)
    print("SNAPSHOT")
    print("=" * 72)

    snapshot = (
        discovery.snapshot()
    )

    print(snapshot)

    assert (
        snapshot["name"]
        == "TwelveDataCommodityDiscovery"
    )

    assert (
        snapshot["version"]
        == "RC2.3"
    )

    print(
        "✅ SNAPSHOT APROVADO"
    )

    # ==========================================================
    # FINAL
    # ==========================================================

    print()
    print("=" * 72)
    print("RESULTADO FINAL")
    print("=" * 72)

    print()
    print(
        "🏆 TWELVE DATA COMMODITY "
        "DISCOVERY RC2.3 APROVADO"
    )


if __name__ == "__main__":

    main()