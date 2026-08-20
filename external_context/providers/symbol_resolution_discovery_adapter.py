"""
external_context/providers/symbol_resolution_discovery_adapter.py

Adapter entre:

    TwelveDataSymbolDiscovery
            ↓
    SemanticSymbolResolutionPipeline

RC2.3

Responsabilidade:

- executar discovery;
- preservar o status original;
- encaminhar candidatos somente quando
  o discovery retornar FOUND;
- nunca transformar erro do provider
  em ausência de candidato.
"""

from external_context.providers.semantic_symbol_resolution_pipeline import (
    SemanticSymbolResolutionPipeline,
)


class SymbolResolutionDiscoveryAdapter:

    NAME = "SymbolResolutionDiscoveryAdapter"

    VERSION = "RC2.3"

    STATUS_FOUND = "FOUND"
    STATUS_NOT_FOUND = "NOT_FOUND"
    STATUS_UNAVAILABLE = "UNAVAILABLE"
    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"

    def __init__(
        self,
        discovery,
        min_confidence: float = 0.80,
    ):

        self.discovery = discovery

        self.pipeline = (
            SemanticSymbolResolutionPipeline(
                min_confidence=min_confidence
            )
        )

        self.last_internal_symbol = ""

        self.last_discovery_status = ""

        self.last_discovery_error = ""

        self.last_candidates = []

        self.last_resolution = {}

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.pipeline.clear()

        self.last_internal_symbol = ""

        self.last_discovery_status = ""

        self.last_discovery_error = ""

        self.last_candidates.clear()

        self.last_resolution = {}

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
    ) -> dict:

        self.clear()

        internal_symbol = str(
            internal_symbol
        ).strip().upper()

        self.last_internal_symbol = (
            internal_symbol
        )

        discovery_result = (
            self.discovery.search(
                internal_symbol
            )
        )

        if not isinstance(
            discovery_result,
            dict,
        ):

            self.last_discovery_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_discovery_error = (
                "Resposta do discovery "
                "inválida."
            )

            return self.snapshot()

        status = str(
            discovery_result.get(
                "status",
                "",
            )
        ).strip().upper()

        error = str(
            discovery_result.get(
                "error",
                "",
            )
        ).strip()

        candidates = (
            discovery_result.get(
                "results",
                [],
            )
        )

        self.last_discovery_status = (
            status
        )

        self.last_discovery_error = (
            error
        )

        if not isinstance(
            candidates,
            list,
        ):

            candidates = []

        self.last_candidates = list(
            candidates
        )

        # ------------------------------------------------------
        # PROVIDER ERROR
        # ------------------------------------------------------

        if status == self.STATUS_PROVIDER_ERROR:

            return self.snapshot()

        # ------------------------------------------------------
        # UNAVAILABLE
        # ------------------------------------------------------

        if status == self.STATUS_UNAVAILABLE:

            return self.snapshot()

        # ------------------------------------------------------
        # NOT FOUND
        # ------------------------------------------------------

        if status == self.STATUS_NOT_FOUND:

            return self.snapshot()

        # ------------------------------------------------------
        # FOUND
        # ------------------------------------------------------

        if status != self.STATUS_FOUND:

            self.last_discovery_status = (
                self.STATUS_PROVIDER_ERROR
            )

            if not self.last_discovery_error:

                self.last_discovery_error = (
                    "Status de discovery "
                    "desconhecido."
                )

            return self.snapshot()

        # ------------------------------------------------------
        # FOUND → SEMANTIC PIPELINE
        # ------------------------------------------------------

        self.last_resolution = (
            self.pipeline.resolve(
                internal_symbol,
                self.last_candidates,
            )
        )

        return self.snapshot()

    # ==========================================================
    # RESOLVED
    # ==========================================================

    def resolved(self) -> bool:

        return bool(
            self.last_resolution.get(
                "resolved",
                False,
            )
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "internal_symbol": (
                self.last_internal_symbol
            ),
            "discovery_status": (
                self.last_discovery_status
            ),
            "discovery_error": (
                self.last_discovery_error
            ),
            "candidate_count": len(
                self.last_candidates
            ),
            "resolution": dict(
                self.last_resolution
            ),
            "resolved": (
                self.resolved()
            ),
        }