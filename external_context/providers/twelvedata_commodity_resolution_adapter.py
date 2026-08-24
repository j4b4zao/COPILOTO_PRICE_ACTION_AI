"""
external_context/providers/twelvedata_commodity_resolution_adapter.py

Twelve Data Commodity Resolution Adapter
RC2.3

Responsabilidade:

    Adaptar o resultado do TwelveDataCommodityDiscovery
    para um formato de resolução padronizado.

Não é responsabilidade desta classe:

    - alterar ProviderSymbolMap;
    - alterar SymbolResolutionEngine;
    - executar descoberta diretamente;
    - aceitar ETFs;
    - aceitar commodities não previstas no perfil.
"""

from __future__ import annotations

from typing import Any


class TwelveDataCommodityResolutionAdapter:
    """
    Adapter entre:

        TwelveDataCommodityDiscovery

    e o fluxo de resolução de símbolos.

    A classe permanece isolada para que a integração
    com o SemanticSymbolResolutionEngine aconteça
    somente após os testes desta camada.
    """

    NAME = (
        "TwelveDataCommodityResolutionAdapter"
    )

    VERSION = "RC2.3"

    VALID_STATUSES = {
        "FOUND",
        "NOT_FOUND",
        "UNAVAILABLE",
        "PROVIDER_ERROR",
    }

    def __init__(
        self,
        discovery: Any,
    ) -> None:

        self.discovery = discovery

        self.internal_symbol = ""
        self.status = ""
        self.symbol: str | None = None
        self.resolved = False
        self.reason = ""
        self.metadata: dict[str, Any] = {}

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
    ) -> dict[str, Any]:

        self.clear()

        internal_symbol = str(
            internal_symbol or ""
        ).strip().upper()

        self.internal_symbol = (
            internal_symbol
        )

        if not internal_symbol:

            self.status = (
                "NOT_FOUND"
            )

            self.reason = (
                "Símbolo interno vazio."
            )

            return self.snapshot()

        result = self.discovery.discover(
            internal_symbol
        )

        if not isinstance(
            result,
            dict,
        ):

            self.status = (
                "PROVIDER_ERROR"
            )

            self.reason = (
                "Resposta do discovery inválida."
            )

            return self.snapshot()

        discovery_status = str(
            result.get(
                "status",
                "",
            )
        ).strip().upper()

        discovery_error = str(
            result.get(
                "error",
                "",
            )
        )

        candidates = result.get(
            "results",
            [],
        )

        if not isinstance(
            candidates,
            list,
        ):

            candidates = []

        self.metadata = {
            "discovery_status":
                discovery_status,
            "candidate_count":
                len(candidates),
        }

        # ------------------------------------------------------
        # STATUS INVÁLIDO
        # ------------------------------------------------------

        if (
            discovery_status
            not in self.VALID_STATUSES
        ):

            self.status = (
                "PROVIDER_ERROR"
            )

            self.reason = (
                "Status de discovery "
                "desconhecido."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # PROVIDER ERROR
        # ------------------------------------------------------

        if (
            discovery_status
            == "PROVIDER_ERROR"
        ):

            self.status = (
                "PROVIDER_ERROR"
            )

            self.reason = (
                discovery_error
                or
                "Provider indisponível."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # UNAVAILABLE
        # ------------------------------------------------------

        if (
            discovery_status
            == "UNAVAILABLE"
        ):

            self.status = (
                "UNAVAILABLE"
            )

            self.reason = (
                discovery_error
                or
                "Recurso indisponível."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # NOT FOUND
        # ------------------------------------------------------

        if (
            discovery_status
            == "NOT_FOUND"
        ):

            self.status = (
                "NOT_FOUND"
            )

            self.reason = (
                discovery_error
                or
                "Nenhuma commodity encontrada."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # FOUND SEM CANDIDATOS
        # ------------------------------------------------------

        if not candidates:

            self.status = (
                "NOT_FOUND"
            )

            self.reason = (
                "Discovery retornou FOUND "
                "sem candidatos."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # CANDIDATO ÚNICO
        # ------------------------------------------------------

        if len(candidates) == 1:

            candidate = candidates[0]

            if not isinstance(
                candidate,
                dict,
            ):

                self.status = (
                    "PROVIDER_ERROR"
                )

                self.reason = (
                    "Candidato inválido."
                )

                return self.snapshot()

            symbol = str(
                candidate.get(
                    "symbol",
                    "",
                )
                or ""
            ).strip()

            if not symbol:

                self.status = (
                    "NOT_FOUND"
                )

                self.reason = (
                    "Candidato sem símbolo válido."
                )

                return self.snapshot()

            self.status = "MAPPED"
            self.symbol = symbol
            self.resolved = True

            self.reason = (
                "Commodity resolvida "
                "com sucesso."
            )

            self.metadata[
                "candidate"
            ] = dict(candidate)

            return self.snapshot()

        # ------------------------------------------------------
        # MÚLTIPLOS CANDIDATOS
        # ------------------------------------------------------

        self.status = (
            "AMBIGUOUS"
        )

        self.reason = (
            "Múltiplos candidatos "
            "compatíveis encontrados."
        )

        self.metadata[
            "candidates"
        ] = [
            dict(candidate)
            for candidate in candidates
            if isinstance(
                candidate,
                dict,
            )
        ]

        return self.snapshot()

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict[str, Any]:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "internal_symbol":
                self.internal_symbol,
            "status": self.status,
            "symbol": self.symbol,
            "resolved": self.resolved,
            "reason": self.reason,
            "metadata": dict(
                self.metadata
            ),
        }

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.internal_symbol = ""
        self.status = ""
        self.symbol = None
        self.resolved = False
        self.reason = ""
        self.metadata = {}