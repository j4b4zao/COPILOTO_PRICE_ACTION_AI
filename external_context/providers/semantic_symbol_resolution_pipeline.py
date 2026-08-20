"""
external_context/providers/semantic_symbol_resolution_pipeline.py

Pipeline semântica para resolução de símbolos.

RC2.3

Fluxo:

Discovery
    ↓
SymbolCandidateFilter
    ↓
SemanticSymbolResolver
    ↓
MAPPED / UNRESOLVED / AMBIGUOUS

Responsabilidade:

- receber candidatos já descobertos;
- aplicar filtro estrutural;
- aplicar resolução semântica;
- preservar candidatos, rejeitados e metadados;
- nunca selecionar automaticamente candidatos
  que não atinjam o nível mínimo de confiança.
"""

from external_context.providers.symbol_candidate_filter import (
    SymbolCandidateFilter,
)

from external_context.providers.semantic_symbol_resolver import (
    SemanticSymbolResolver,
)


class SemanticSymbolResolutionPipeline:

    NAME = "SemanticSymbolResolutionPipeline"

    VERSION = "RC2.3"

    STATUS_MAPPED = "MAPPED"

    STATUS_UNRESOLVED = "UNRESOLVED"

    STATUS_AMBIGUOUS = "AMBIGUOUS"

    def __init__(
        self,
        min_confidence: float = 0.80,
    ):

        self.filter = (
            SymbolCandidateFilter()
        )

        self.resolver = (
            SemanticSymbolResolver(
                min_confidence=min_confidence
            )
        )

        self.last_internal_symbol = ""

        self.last_status = ""

        self.last_symbol = None

        self.last_reason = ""

        self.last_confidence = 0.0

        self.last_candidates = []

        self.last_accepted = []

        self.last_rejected = []

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.filter.clear()

        self.resolver.clear()

        self.last_internal_symbol = ""

        self.last_status = ""

        self.last_symbol = None

        self.last_reason = ""

        self.last_confidence = 0.0

        self.last_candidates.clear()

        self.last_accepted.clear()

        self.last_rejected.clear()

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
        candidates: list[dict],
    ) -> dict:
        """
        Executa:

            candidates
                ↓
            structural filter
                ↓
            semantic resolver
        """

        self.clear()

        internal_symbol = str(
            internal_symbol
        ).strip().upper()

        self.last_internal_symbol = (
            internal_symbol
        )

        self.last_candidates = list(
            candidates
            if isinstance(
                candidates,
                list,
            )
            else []
        )

        # ------------------------------------------------------
        # FILTER
        # ------------------------------------------------------

        accepted = self.filter.filter(
            internal_symbol,
            self.last_candidates,
        )

        self.last_accepted = list(
            accepted
        )

        self.last_rejected = (
            self.filter.rejected()
        )

        # ------------------------------------------------------
        # RESOLVER
        # ------------------------------------------------------

        resolver_result = (
            self.resolver.resolve(
                internal_symbol,
                accepted,
            )
        )

        self.last_status = (
            resolver_result["status"]
        )

        self.last_symbol = (
            resolver_result["symbol"]
        )

        self.last_confidence = (
            resolver_result["confidence"]
        )

        self.last_reason = (
            resolver_result["reason"]
        )

        # ------------------------------------------------------
        # RESULTADO
        # ------------------------------------------------------

        return self.snapshot()

    # ==========================================================
    # RESOLVED
    # ==========================================================

    def resolved(self) -> bool:

        return (
            self.last_status
            == self.STATUS_MAPPED
            and self.last_symbol
            is not None
        )

    # ==========================================================
    # SYMBOL
    # ==========================================================

    def symbol(
        self,
    ) -> str | None:

        return self.last_symbol

    # ==========================================================
    # STATUS
    # ==========================================================

    def status(
        self,
    ) -> str:

        return self.last_status

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
            "status": (
                self.last_status
            ),
            "symbol": (
                self.last_symbol
            ),
            "resolved": (
                self.resolved()
            ),
            "confidence": (
                self.last_confidence
            ),
            "reason": (
                self.last_reason
            ),
            "candidate_count": len(
                self.last_candidates
            ),
            "accepted_count": len(
                self.last_accepted
            ),
            "rejected_count": len(
                self.last_rejected
            ),
            "accepted": list(
                self.last_accepted
            ),
            "rejected": list(
                self.last_rejected
            ),
            "resolver": (
                self.resolver.snapshot()
            ),
            "filter": (
                self.filter.snapshot()
            ),
        }