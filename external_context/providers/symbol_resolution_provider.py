"""
external_context/providers/symbol_resolution_provider.py

Adaptador entre o TwelveDataSymbolDiscovery e o
SymbolResolutionEngine.

RC2.2

Responsabilidades:

- executar discovery;
- interpretar corretamente o resultado;
- separar descoberta de resolução;
- impedir seleção automática de instrumento ambíguo;
- preservar candidatos e metadados;
- encaminhar somente símbolos realmente resolvidos
  para o SymbolResolutionEngine.

Estados de resolução:

MAPPED
UNRESOLVED
AMBIGUOUS
NOT_FOUND
UNAVAILABLE
PROVIDER_ERROR
INVALID_QUERY
"""

from external_context.providers.symbol_resolution_engine import (
    SymbolResolutionEngine,
)

from external_context.providers.twelvedata_symbol_discovery import (
    TwelveDataSymbolDiscovery,
)


class SymbolResolutionProvider:

    NAME = "SymbolResolutionProvider"

    VERSION = "RC2.2"

    STATUS_MAPPED = "MAPPED"
    STATUS_UNRESOLVED = "UNRESOLVED"
    STATUS_AMBIGUOUS = "AMBIGUOUS"
    STATUS_NOT_FOUND = "NOT_FOUND"
    STATUS_UNAVAILABLE = "UNAVAILABLE"
    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"
    STATUS_INVALID_QUERY = "INVALID_QUERY"

    def __init__(
        self,
        discovery: TwelveDataSymbolDiscovery,
        engine: SymbolResolutionEngine,
    ):

        self.discovery = discovery
        self.engine = engine

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        internal_symbol: str,
        query: str | None = None,
    ):

        internal_symbol = str(
            internal_symbol
        ).strip()

        # ------------------------------------------------------
        # QUERY INVÁLIDA
        # ------------------------------------------------------

        if not internal_symbol:

            return self.engine.resolve(
                internal_symbol="",
                provider_symbol=None,
                discovery_status=self.STATUS_INVALID_QUERY,
                reason="Símbolo interno vazio.",
            )

        search_query = (
            query
            if query is not None
            else internal_symbol
        )

        search_query = str(
            search_query
        ).strip()

        if not search_query:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_INVALID_QUERY,
                reason="Consulta de símbolo vazia.",
            )

        # ------------------------------------------------------
        # DISCOVERY
        # ------------------------------------------------------

        results = self.discovery.search(
            search_query
        )

        status = (
            self.discovery.last_status
        )

        error = (
            self.discovery.last_error
            or ""
        )

        # ------------------------------------------------------
        # PROVIDER ERROR
        # ------------------------------------------------------

        if status == self.STATUS_PROVIDER_ERROR:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_PROVIDER_ERROR,
                reason=error,
            )

        # ------------------------------------------------------
        # UNAVAILABLE
        # ------------------------------------------------------

        if status == self.STATUS_UNAVAILABLE:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_UNAVAILABLE,
                reason=error,
            )

        # ------------------------------------------------------
        # INVALID QUERY
        # ------------------------------------------------------

        if status == self.STATUS_INVALID_QUERY:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_INVALID_QUERY,
                reason=error,
            )

        # ------------------------------------------------------
        # NOT FOUND
        # ------------------------------------------------------

        if status == self.STATUS_NOT_FOUND:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_NOT_FOUND,
                reason=(
                    error
                    or "Símbolo não encontrado."
                ),
            )

        # ------------------------------------------------------
        # STATUS DIFERENTE DE FOUND
        # ------------------------------------------------------

        if status != "FOUND":

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_PROVIDER_ERROR,
                reason=(
                    "Status desconhecido retornado "
                    "pelo Discovery."
                ),
                metadata={
                    "discovery_status": status,
                    "error": error,
                },
            )

        # ------------------------------------------------------
        # FOUND
        # ------------------------------------------------------

        if not isinstance(
            results,
            list,
        ):

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_PROVIDER_ERROR,
                reason=(
                    "Discovery retornou dados "
                    "em formato inválido."
                ),
            )

        # ------------------------------------------------------
        # NENHUM CANDIDATO
        # ------------------------------------------------------

        if not results:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_NOT_FOUND,
                reason=(
                    "Discovery informou FOUND, "
                    "mas não retornou candidatos."
                ),
            )

        # ------------------------------------------------------
        # BUSCA MATCH EXATO
        # ------------------------------------------------------

        target = search_query.upper()

        exact_matches = []

        for item in results:

            if not isinstance(
                item,
                dict,
            ):
                continue

            symbol = str(
                item.get(
                    "symbol",
                    "",
                )
            ).strip()

            if (
                symbol.upper()
                == target
            ):

                exact_matches.append(
                    item
                )

        # ------------------------------------------------------
        # FOUND + ZERO MATCH EXATO
        # ------------------------------------------------------

        if not exact_matches:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_UNRESOLVED,
                reason=(
                    "Candidatos encontrados, "
                    "mas nenhum possui símbolo "
                    "exato para a consulta."
                ),
                metadata={
                    "candidate_count": len(
                        results
                    ),
                    "candidates": list(
                        results
                    ),
                    "query": search_query,
                },
            )

        # ------------------------------------------------------
        # MAIS DE UM MATCH EXATO
        # ------------------------------------------------------

        if len(exact_matches) > 1:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_AMBIGUOUS,
                reason=(
                    "Múltiplos candidatos exatos "
                    "encontrados; seleção automática "
                    "bloqueada."
                ),
                metadata={
                    "candidate_count": len(
                        exact_matches
                    ),
                    "candidates": list(
                        exact_matches
                    ),
                    "query": search_query,
                },
            )

        # ------------------------------------------------------
        # MATCH ÚNICO
        # ------------------------------------------------------

        candidate = exact_matches[0]

        provider_symbol = str(
            candidate.get(
                "symbol",
                "",
            )
        ).strip()

        if not provider_symbol:

            return self.engine.resolve(
                internal_symbol=internal_symbol,
                provider_symbol=None,
                discovery_status=self.STATUS_UNRESOLVED,
                reason=(
                    "Candidato encontrado sem "
                    "símbolo válido."
                ),
                metadata={
                    "candidate": candidate,
                    "query": search_query,
                },
            )

        return self.engine.resolve(
            internal_symbol=internal_symbol,
            provider_symbol=provider_symbol,
            discovery_status=self.STATUS_MAPPED,
            reason=(
                "Símbolo encontrado com "
                "correspondência exata."
            ),
            metadata=candidate,
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "discovery": {
                "name": self.discovery.NAME,
                "version": self.discovery.VERSION,
                "last_status": (
                    self.discovery.last_status
                ),
                "last_error": (
                    self.discovery.last_error
                ),
            },
            "engine": (
                self.engine.snapshot()
            ),
        }