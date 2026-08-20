"""
external_context/providers/semantic_symbol_resolution_engine.py

Semantic Symbol Resolution Engine.

RC2.3

Responsabilidades:

- Resolver símbolos individualmente.
- Resolver símbolos em lote.
- Consumir SemanticSymbolResolutionPipeline.
- Preservar os estados de resolução.
- Adicionar ao mapa SOMENTE resultados MAPPED válidos.
- Bloquear resultados inválidos ou desconhecidos.
"""

from typing import Any


class SemanticSymbolResolutionEngine:

    NAME = "SemanticSymbolResolutionEngine"

    VERSION = "RC2.3"

    STATUS_MAPPED = "MAPPED"
    STATUS_UNRESOLVED = "UNRESOLVED"
    STATUS_AMBIGUOUS = "AMBIGUOUS"
    STATUS_UNAVAILABLE = "UNAVAILABLE"
    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"
    STATUS_NOT_FOUND = "NOT_FOUND"

    VALID_STATUSES = {
        STATUS_MAPPED,
        STATUS_UNRESOLVED,
        STATUS_AMBIGUOUS,
        STATUS_UNAVAILABLE,
        STATUS_PROVIDER_ERROR,
        STATUS_NOT_FOUND,
    }

    def __init__(self, pipeline):

        self.pipeline = pipeline

        self.resolved: dict[str, str] = {}

        self.results: dict[str, dict] = {}

        self.unavailable: list[str] = []

        self.ambiguous: list[str] = []

        self.unresolved: list[str] = []

        self.provider_errors: list[str] = []

        self.not_found: list[str] = []

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.resolved.clear()
        self.results.clear()

        self.unavailable.clear()
        self.ambiguous.clear()
        self.unresolved.clear()
        self.provider_errors.clear()
        self.not_found.clear()

    # ==========================================================
    # NORMALIZE RESULT
    # ==========================================================

    def _normalize_result(
        self,
        internal_symbol: str,
        result: Any,
        candidate_count: int,
    ) -> dict:

        if not isinstance(result, dict):

            return {
                "name": (
                    "SemanticSymbolResolutionPipeline"
                ),
                "version": self.VERSION,
                "internal_symbol": internal_symbol,
                "status": self.STATUS_PROVIDER_ERROR,
                "symbol": None,
                "resolved": False,
                "confidence": 0.0,
                "reason": (
                    "Resposta do pipeline inválida."
                ),
                "candidate_count": candidate_count,
            }

        normalized = dict(result)

        status = str(
            normalized.get(
                "status",
                "",
            )
        ).strip().upper()

        if status not in self.VALID_STATUSES:

            normalized["status"] = (
                self.STATUS_PROVIDER_ERROR
            )

            normalized["symbol"] = None

            normalized["resolved"] = False

            normalized["reason"] = (
                "Status de resolução desconhecido."
            )

            normalized["candidate_count"] = (
                candidate_count
            )

            return normalized

        normalized.setdefault(
            "internal_symbol",
            internal_symbol,
        )

        normalized.setdefault(
            "symbol",
            None,
        )

        normalized.setdefault(
            "resolved",
            False,
        )

        normalized.setdefault(
            "confidence",
            0.0,
        )

        normalized.setdefault(
            "reason",
            "",
        )

        normalized.setdefault(
            "candidate_count",
            candidate_count,
        )

        return normalized

    # ==========================================================
    # REGISTER STATUS
    # ==========================================================

    def _register_status(
        self,
        internal_symbol: str,
        status: str,
    ) -> None:

        if status == self.STATUS_UNAVAILABLE:

            if (
                internal_symbol
                not in self.unavailable
            ):
                self.unavailable.append(
                    internal_symbol
                )

        elif status == self.STATUS_AMBIGUOUS:

            if (
                internal_symbol
                not in self.ambiguous
            ):
                self.ambiguous.append(
                    internal_symbol
                )

        elif status == self.STATUS_UNRESOLVED:

            if (
                internal_symbol
                not in self.unresolved
            ):
                self.unresolved.append(
                    internal_symbol
                )

        elif status == self.STATUS_PROVIDER_ERROR:

            if (
                internal_symbol
                not in self.provider_errors
            ):
                self.provider_errors.append(
                    internal_symbol
                )

        elif status == self.STATUS_NOT_FOUND:

            if (
                internal_symbol
                not in self.not_found
            ):
                self.not_found.append(
                    internal_symbol
                )

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
        candidates: list[dict],
    ) -> dict:

        internal_symbol = str(
            internal_symbol
        ).strip().upper()

        if not isinstance(
            candidates,
            list,
        ):

            candidates = []

        candidate_count = len(
            candidates
        )

        # ------------------------------------------------------
        # PIPELINE
        # ------------------------------------------------------

        try:

            result = self.pipeline.resolve(
                internal_symbol,
                candidates,
            )

        except Exception as exc:

            result = {
                "name": (
                    "SemanticSymbolResolutionPipeline"
                ),
                "version": self.VERSION,
                "internal_symbol": internal_symbol,
                "status": (
                    self.STATUS_PROVIDER_ERROR
                ),
                "symbol": None,
                "resolved": False,
                "confidence": 0.0,
                "reason": (
                    f"Erro no pipeline: {exc}"
                ),
                "candidate_count": candidate_count,
            }

        result = self._normalize_result(
            internal_symbol,
            result,
            candidate_count,
        )

        status = result["status"]

        symbol = result.get(
            "symbol"
        )

        # ------------------------------------------------------
        # MAPPED
        # ------------------------------------------------------

        if status == self.STATUS_MAPPED:

            # MAPPED exige símbolo válido.

            if not isinstance(
                symbol,
                str,
            ) or not symbol.strip():

                result["status"] = (
                    self.STATUS_UNRESOLVED
                )

                result["symbol"] = None

                result["resolved"] = False

                result["reason"] = (
                    "Status MAPPED sem "
                    "símbolo válido."
                )

                status = (
                    self.STATUS_UNRESOLVED
                )

            else:

                symbol = symbol.strip()

                result["symbol"] = symbol

                result["resolved"] = True

                self.resolved[
                    internal_symbol
                ] = symbol

        # ------------------------------------------------------
        # NÃO MAPPED
        # ------------------------------------------------------

        if status != self.STATUS_MAPPED:

            # Garantia estrutural:
            # nenhum estado não-MAPPED entra no mapa.

            self.resolved.pop(
                internal_symbol,
                None,
            )

            result["symbol"] = None

            result["resolved"] = False

            self._register_status(
                internal_symbol,
                status,
            )

        self.results[
            internal_symbol
        ] = result

        return result

    # ==========================================================
    # RESOLVE MANY
    # ==========================================================

    def resolve_many(
        self,
        candidates_by_symbol: dict[
            str,
            list[dict],
        ],
    ) -> dict:

        self.clear()

        if not isinstance(
            candidates_by_symbol,
            dict,
        ):

            return self.snapshot()

        for (
            internal_symbol,
            candidates,
        ) in candidates_by_symbol.items():

            self.resolve(
                internal_symbol,
                candidates,
            )

        return self.snapshot()

    # ==========================================================
    # MAPPING
    # ==========================================================

    def mapping(self) -> dict:

        return dict(
            self.resolved
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "resolved": dict(
                self.resolved
            ),
            "unavailable": list(
                self.unavailable
            ),
            "ambiguous": list(
                self.ambiguous
            ),
            "unresolved": list(
                self.unresolved
            ),
            "provider_errors": list(
                self.provider_errors
            ),
            "not_found": list(
                self.not_found
            ),
            "count": len(
                self.resolved
            ),
            "results": dict(
                self.results
            ),
        }