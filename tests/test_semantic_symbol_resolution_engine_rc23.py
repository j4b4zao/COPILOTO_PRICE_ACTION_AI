"""
tests/test_semantic_symbol_resolution_engine_rc23.py

Teste de integração controlado do
SemanticSymbolResolutionEngine RC2.3.

Objetivo:

    Validar a integração entre:

        - Index Resolution
        - Commodity Resolution Adapter
        - Semantic Resolution
        - classificação final dos estados

Sem utilizar API real.

Este teste NÃO altera o Engine de produção.
"""

from __future__ import annotations

from typing import Any

from external_context.providers.twelvedata_commodity_resolution_adapter import (
    TwelveDataCommodityResolutionAdapter,
)


# ==============================================================
# FAKE INDEX DISCOVERY
# ==============================================================

class FakeIndexDiscovery:
    """
    Discovery controlado para índices.
    """

    def __init__(
        self,
        responses: dict[str, dict[str, Any]],
    ) -> None:

        self.responses = responses

    def discover(
        self,
        internal_symbol: str,
    ) -> dict[str, Any]:

        return self.responses.get(
            internal_symbol,
            {
                "status": "NOT_FOUND",
                "error": "Nenhum candidato.",
                "results": [],
            },
        )


# ==============================================================
# FAKE COMMODITY DISCOVERY
# ==============================================================

class FakeCommodityDiscovery:
    """
    Discovery controlado para commodities.
    """

    def __init__(
        self,
        responses: dict[str, dict[str, Any]],
    ) -> None:

        self.responses = responses

    def discover(
        self,
        internal_symbol: str,
    ) -> dict[str, Any]:

        return self.responses.get(
            internal_symbol,
            {
                "status": "NOT_FOUND",
                "error": "Nenhuma commodity.",
                "results": [],
            },
        )


# ==============================================================
# RC2.3 INTEGRATION ENGINE
# ==============================================================

class SemanticSymbolResolutionEngineRC23:
    """
    Engine controlado utilizado exclusivamente no teste.

    Ele demonstra a arquitetura esperada para a integração
    sem modificar o Engine de produção.

    Índices:

        discovery → resultado

    Commodities:

        discovery
            ↓
        commodity adapter
            ↓
        resultado
    """

    NAME = (
        "SemanticSymbolResolutionEngine"
    )

    VERSION = "RC2.3"

    def __init__(
        self,
        index_discovery: Any,
        commodity_adapter: Any,
    ) -> None:

        self.index_discovery = (
            index_discovery
        )

        self.commodity_adapter = (
            commodity_adapter
        )

        self.resolved: dict[
            str,
            str,
        ] = {}

        self.unavailable: list[
            str
        ] = []

        self.ambiguous: list[
            str
        ] = []

        self.unresolved: list[
            str
        ] = []

        self.provider_errors: list[
            str
        ] = []

        self.not_found: list[
            str
        ] = []

        self.results: dict[
            str,
            dict[str, Any],
        ] = {}

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
    ) -> dict[str, Any]:

        internal_symbol = str(
            internal_symbol or ""
        ).strip().upper()

        if not internal_symbol:

            result = {
                "internal_symbol": "",
                "status": "NOT_FOUND",
                "symbol": None,
                "resolved": False,
                "reason": (
                    "Símbolo interno vazio."
                ),
            }

            return result

        # ------------------------------------------------------
        # COMMODITIES
        # ------------------------------------------------------

        if internal_symbol in {
            "OIL",
            "GOLD",
        }:

            result = (
                self.commodity_adapter
                .resolve(
                    internal_symbol
                )
            )

            return self._register(
                internal_symbol,
                result,
            )

        # ------------------------------------------------------
        # ÍNDICES
        # ------------------------------------------------------

        discovery = (
            self.index_discovery
            .discover(
                internal_symbol
            )
        )

        status = str(
            discovery.get(
                "status",
                "",
            )
        ).strip().upper()

        error = str(
            discovery.get(
                "error",
                "",
            )
        )

        candidates = discovery.get(
            "results",
            [],
        )

        if not isinstance(
            candidates,
            list,
        ):

            candidates = []

        # ------------------------------------------------------
        # PROVIDER ERROR
        # ------------------------------------------------------

        if status == "PROVIDER_ERROR":

            result = {
                "internal_symbol":
                    internal_symbol,
                "status":
                    "PROVIDER_ERROR",
                "symbol": None,
                "resolved": False,
                "reason":
                    error
                    or
                    "Provider indisponível.",
            }

            return self._register(
                internal_symbol,
                result,
            )

        # ------------------------------------------------------
        # UNAVAILABLE
        # ------------------------------------------------------

        if status == "UNAVAILABLE":

            result = {
                "internal_symbol":
                    internal_symbol,
                "status":
                    "UNAVAILABLE",
                "symbol": None,
                "resolved": False,
                "reason":
                    error
                    or
                    "Plano sem acesso.",
            }

            return self._register(
                internal_symbol,
                result,
            )

        # ------------------------------------------------------
        # NOT FOUND
        # ------------------------------------------------------

        if (
            status == "NOT_FOUND"
            or not candidates
        ):

            result = {
                "internal_symbol":
                    internal_symbol,
                "status":
                    "NOT_FOUND",
                "symbol": None,
                "resolved": False,
                "reason":
                    error
                    or
                    "Nenhum candidato.",
            }

            return self._register(
                internal_symbol,
                result,
            )

        # ------------------------------------------------------
        # CANDIDATO ÚNICO
        # ------------------------------------------------------

        if len(candidates) == 1:

            candidate = candidates[0]

            if not isinstance(
                candidate,
                dict,
            ):

                result = {
                    "internal_symbol":
                        internal_symbol,
                    "status":
                        "UNRESOLVED",
                    "symbol": None,
                    "resolved": False,
                    "reason":
                        "Candidato inválido.",
                }

                return self._register(
                    internal_symbol,
                    result,
                )

            symbol = str(
                candidate.get(
                    "symbol",
                    "",
                )
                or ""
            ).strip()

            if not symbol:

                result = {
                    "internal_symbol":
                        internal_symbol,
                    "status":
                        "UNRESOLVED",
                    "symbol": None,
                    "resolved": False,
                    "reason":
                        "Candidato sem símbolo.",
                }

                return self._register(
                    internal_symbol,
                    result,
                )

            result = {
                "internal_symbol":
                    internal_symbol,
                "status":
                    "MAPPED",
                "symbol":
                    symbol,
                "resolved":
                    True,
                "reason":
                    "Candidato resolvido.",
            }

            return self._register(
                internal_symbol,
                result,
            )

        # ------------------------------------------------------
        # MÚLTIPLOS
        # ------------------------------------------------------

        result = {
            "internal_symbol":
                internal_symbol,
            "status":
                "AMBIGUOUS",
            "symbol": None,
            "resolved": False,
            "reason":
                "Múltiplos candidatos.",
        }

        return self._register(
            internal_symbol,
            result,
        )

    # ==========================================================
    # REGISTER
    # ==========================================================

    def _register(
        self,
        internal_symbol: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:

        status = str(
            result.get(
                "status",
                "",
            )
        ).upper()

        self.results[
            internal_symbol
        ] = dict(result)

        if status == "MAPPED":

            symbol = result.get(
                "symbol"
            )

            if symbol:

                self.resolved[
                    internal_symbol
                ] = symbol

        elif status == "UNAVAILABLE":

            self.unavailable.append(
                internal_symbol
            )

        elif status == "AMBIGUOUS":

            self.ambiguous.append(
                internal_symbol
            )

        elif status == "UNRESOLVED":

            self.unresolved.append(
                internal_symbol
            )

        elif status == "PROVIDER_ERROR":

            self.provider_errors.append(
                internal_symbol
            )

        elif status == "NOT_FOUND":

            self.not_found.append(
                internal_symbol
            )

        return result

    # ==========================================================
    # RESOLVE MANY
    # ==========================================================

    def resolve_many(
        self,
        symbols: list[str],
    ) -> dict[str, dict[str, Any]]:

        for symbol in symbols:

            self.resolve(symbol)

        return dict(
            self.results
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict[str, Any]:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "resolved":
                dict(self.resolved),
            "unavailable":
                list(self.unavailable),
            "ambiguous":
                list(self.ambiguous),
            "unresolved":
                list(self.unresolved),
            "provider_errors":
                list(self.provider_errors),
            "not_found":
                list(self.not_found),
            "count":
                len(self.resolved),
            "results":
                dict(self.results),
        }

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.resolved.clear()
        self.unavailable.clear()
        self.ambiguous.clear()
        self.unresolved.clear()
        self.provider_errors.clear()
        self.not_found.clear()
        self.results.clear()


# ==============================================================
# TESTS
# ==============================================================

def main():

    print("=" * 72)
    print(
        "TESTE SEMANTIC SYMBOL RESOLUTION "
        "ENGINE RC2.3"
    )
    print("=" * 72)

    # ==========================================================
    # DISCOVERY DE ÍNDICES
    # ==========================================================

    index_discovery = FakeIndexDiscovery(
        {

            "NASDAQ": {
                "status": "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol":
                            "TEST_NASDAQ",
                        "name":
                            "Nasdaq Composite Index",
                        "type":
                            "Index",
                        "country":
                            "United States",
                    }
                ],
            },

            "US500": {
                "status":
                    "UNAVAILABLE",
                "error":
                    "Plano sem acesso.",
                "results": [],
            },

            "DXY": {
                "status":
                    "FOUND",
                "error": "",
                "results": [
                    {
                        "symbol":
                            "TEST_DXY_A",
                        "name":
                            "US Dollar Index",
                        "type":
                            "Index",
                        "country":
                            "United States",
                    },
                    {
                        "symbol":
                            "TEST_DXY_B",
                        "name":
                            "US Dollar Index",
                        "type":
                            "Index",
                        "country":
                            "United States",
                    },
                ],
            },

            "VIX": {
                "status":
                    "PROVIDER_ERROR",
                "error":
                    "Provider indisponível.",
                "results": [],
            },

            "GOLD_INDEX_TEST": {
                "status":
                    "NOT_FOUND",
                "error":
                    "Nenhum candidato.",
                "results": [],
            },
        }
    )

    # ==========================================================
    # DISCOVERY DE COMMODITIES
    # ==========================================================

    commodity_discovery = (
        FakeCommodityDiscovery(
            {

                "OIL": {
                    "status":
                        "FOUND",
                    "error": "",
                    "results": [
                        {
                            "symbol":
                                "WTI/USD",
                            "name":
                                "Crude Oil WTI Spot",
                            "category":
                                "Energy Resource",
                        }
                    ],
                },

                "GOLD": {
                    "status":
                        "FOUND",
                    "error": "",
                    "results": [
                        {
                            "symbol":
                                "XAU/USD",
                            "name":
                                "Gold Spot",
                            "category":
                                "Precious Metal",
                        }
                    ],
                },
            }
        )
    )

    commodity_adapter = (
        TwelveDataCommodityResolutionAdapter(
            commodity_discovery
        )
    )

    engine = (
        SemanticSymbolResolutionEngineRC23(
            index_discovery,
            commodity_adapter,
        )
    )

    # ==========================================================
    # MAPPED NASDAQ
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: NASDAQ → MAPPED")
    print("=" * 72)

    result = engine.resolve(
        "NASDAQ"
    )

    print(result)

    assert result["status"] == "MAPPED"
    assert (
        result["symbol"]
        == "TEST_NASDAQ"
    )
    assert result["resolved"] is True

    print("✅ NASDAQ MAPPED APROVADO")

    # ==========================================================
    # OIL
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: OIL → WTI/USD")
    print("=" * 72)

    result = engine.resolve(
        "OIL"
    )

    print(result)

    assert result["status"] == "MAPPED"
    assert (
        result["symbol"]
        == "WTI/USD"
    )
    assert result["resolved"] is True

    print("✅ OIL → WTI/USD APROVADO")

    # ==========================================================
    # GOLD
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: GOLD → XAU/USD")
    print("=" * 72)

    result = engine.resolve(
        "GOLD"
    )

    print(result)

    assert result["status"] == "MAPPED"
    assert (
        result["symbol"]
        == "XAU/USD"
    )
    assert result["resolved"] is True

    print("✅ GOLD → XAU/USD APROVADO")

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: US500 → UNAVAILABLE")
    print("=" * 72)

    result = engine.resolve(
        "US500"
    )

    print(result)

    assert (
        result["status"]
        == "UNAVAILABLE"
    )
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ US500 UNAVAILABLE BLOQUEADO")

    # ==========================================================
    # AMBIGUOUS
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: DXY → AMBIGUOUS")
    print("=" * 72)

    result = engine.resolve(
        "DXY"
    )

    print(result)

    assert (
        result["status"]
        == "AMBIGUOUS"
    )
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ DXY AMBIGUOUS BLOQUEADO")

    # ==========================================================
    # PROVIDER ERROR
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: VIX → PROVIDER_ERROR")
    print("=" * 72)

    result = engine.resolve(
        "VIX"
    )

    print(result)

    assert (
        result["status"]
        == "PROVIDER_ERROR"
    )
    assert result["symbol"] is None
    assert result["resolved"] is False

    print("✅ VIX PROVIDER_ERROR BLOQUEADO")

    # ==========================================================
    # CENÁRIO MISTO
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: CENÁRIO MISTO")
    print("=" * 72)

    engine.clear()

    engine.resolve_many(
        [
            "NASDAQ",
            "OIL",
            "GOLD",
            "US500",
            "DXY",
            "VIX",
            "GOLD_INDEX_TEST",
        ]
    )

    snapshot = engine.snapshot()

    print()
    print("RESOLVIDOS")
    print("-" * 72)
    print(
        snapshot["resolved"]
    )

    print()
    print("UNAVAILABLE")
    print("-" * 72)
    print(
        snapshot["unavailable"]
    )

    print()
    print("AMBIGUOUS")
    print("-" * 72)
    print(
        snapshot["ambiguous"]
    )

    print()
    print("PROVIDER ERRORS")
    print("-" * 72)
    print(
        snapshot["provider_errors"]
    )

    print()
    print("NOT FOUND")
    print("-" * 72)
    print(
        snapshot["not_found"]
    )

    assert (
        snapshot["resolved"]
        == {
            "NASDAQ":
                "TEST_NASDAQ",
            "OIL":
                "WTI/USD",
            "GOLD":
                "XAU/USD",
        }
    )

    assert (
        snapshot["unavailable"]
        == ["US500"]
    )

    assert (
        snapshot["ambiguous"]
        == ["DXY"]
    )

    assert (
        snapshot["provider_errors"]
        == ["VIX"]
    )

    assert (
        snapshot["not_found"]
        == [
            "GOLD_INDEX_TEST"
        ]
    )

    print()
    print(
        "✅ CENÁRIO MISTO APROVADO"
    )

    # ==========================================================
    # MAPA FINAL
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: MAPA FINAL")
    print("=" * 72)

    print(
        snapshot["resolved"]
    )

    assert (
        snapshot["resolved"][
            "OIL"
        ]
        == "WTI/USD"
    )

    assert (
        snapshot["resolved"][
            "GOLD"
        ]
        == "XAU/USD"
    )

    print(
        "✅ MAPA FINAL APROVADO"
    )

    # ==========================================================
    # CLEAR
    # ==========================================================

    print()
    print("=" * 72)
    print("TESTE: CLEAR")
    print("=" * 72)

    engine.clear()

    snapshot = engine.snapshot()

    print(snapshot)

    assert (
        snapshot["resolved"]
        == {}
    )

    assert (
        snapshot["unavailable"]
        == []
    )

    assert (
        snapshot["ambiguous"]
        == []
    )

    assert (
        snapshot["unresolved"]
        == []
    )

    assert (
        snapshot["provider_errors"]
        == []
    )

    assert (
        snapshot["not_found"]
        == []
    )

    assert (
        snapshot["count"]
        == 0
    )

    assert (
        snapshot["results"]
        == {}
    )

    print(
        "✅ CLEAR APROVADO"
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
        "🏆 SEMANTIC SYMBOL RESOLUTION "
        "ENGINE RC2.3 APROVADO"
    )


if __name__ == "__main__":
    main()