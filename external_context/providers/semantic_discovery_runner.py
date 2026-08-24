"""
external_context/providers/semantic_discovery_runner.py

Executa discovery usando as consultas semânticas
definidas em InstrumentProfiles.

RC2.3

Compatibilidade:

    FakeDiscovery / testes:
        search() -> dict

    TwelveDataSymbolDiscovery:
        search() -> list[dict]
        last_status
        last_error

Fluxo:

internal symbol
      ↓
InstrumentProfiles
      ↓
queries semânticas
      ↓
Discovery
      ↓
candidatos
"""

from external_context.providers.instrument_profiles import (
    InstrumentProfiles,
)


class SemanticDiscoveryRunner:

    NAME = "SemanticDiscoveryRunner"

    VERSION = "RC2.3"

    STATUS_FOUND = "FOUND"

    STATUS_NOT_FOUND = "NOT_FOUND"

    STATUS_UNAVAILABLE = "UNAVAILABLE"

    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"

    STATUS_INVALID_QUERY = "INVALID_QUERY"

    # ==========================================================
    # CONSTRUTOR
    # ==========================================================

    def __init__(
        self,
        discovery,
    ):

        self.discovery = discovery

        self.last_internal_symbol = ""

        self.last_query = ""

        self.last_status = ""

        self.last_error = ""

        self.last_results = []

        self.last_queries = []

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.last_internal_symbol = ""

        self.last_query = ""

        self.last_status = ""

        self.last_error = ""

        self.last_results.clear()

        self.last_queries.clear()

    # ==========================================================
    # NORMALIZAR RESPOSTA DO DISCOVERY
    # ==========================================================

    def _normalize_response(
        self,
        response,
    ) -> tuple[str, str, list[dict]]:

        # ------------------------------------------------------
        # INTERFACE REAL:
        #
        # search() -> list[dict]
        # status    -> discovery.last_status
        # error     -> discovery.last_error
        # ------------------------------------------------------

        if isinstance(
            response,
            list,
        ):

            status = str(
                getattr(
                    self.discovery,
                    "last_status",
                    "",
                )
            ).strip().upper()

            error = str(
                getattr(
                    self.discovery,
                    "last_error",
                    "",
                )
            ).strip()

            results = [
                item
                for item in response
                if isinstance(
                    item,
                    dict,
                )
            ]

            return (
                status,
                error,
                results,
            )

        # ------------------------------------------------------
        # INTERFACE TESTE:
        #
        # search() -> dict
        # ------------------------------------------------------

        if isinstance(
            response,
            dict,
        ):

            status = str(
                response.get(
                    "status",
                    "",
                )
            ).strip().upper()

            error = str(
                response.get(
                    "error",
                    "",
                )
            ).strip()

            results = response.get(
                "results",
                [],
            )

            if not isinstance(
                results,
                list,
            ):

                results = []

            results = [
                item
                for item in results
                if isinstance(
                    item,
                    dict,
                )
            ]

            return (
                status,
                error,
                results,
            )

        # ------------------------------------------------------
        # RESPOSTA INVÁLIDA
        # ------------------------------------------------------

        return (
            self.STATUS_PROVIDER_ERROR,
            "Resposta do discovery inválida.",
            [],
        )

    # ==========================================================
    # SEARCH
    # ==========================================================

    def search(
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

        # ------------------------------------------------------
        # PERFIL
        # ------------------------------------------------------

        profile = (
            InstrumentProfiles.get(
                internal_symbol
            )
        )

        if profile is None:

            self.last_status = (
                self.STATUS_NOT_FOUND
            )

            self.last_error = (
                "Perfil de instrumento "
                "não encontrado."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # QUERIES
        # ------------------------------------------------------

        queries = list(
            profile.get(
                "queries",
                [],
            )
        )

        self.last_queries = list(
            queries
        )

        if not queries:

            self.last_status = (
                self.STATUS_NOT_FOUND
            )

            self.last_error = (
                "Nenhuma consulta semântica "
                "disponível."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # EXECUTAR QUERIES
        # ------------------------------------------------------

        for query in queries:

            query = str(
                query
            ).strip()

            if not query:

                continue

            self.last_query = query

            # --------------------------------------------------
            # DISCOVERY
            # --------------------------------------------------

            try:

                response = (
                    self.discovery.search(
                        query
                    )
                )

            except Exception as exc:

                self.last_status = (
                    self.STATUS_PROVIDER_ERROR
                )

                self.last_error = (
                    f"Erro inesperado no "
                    f"discovery: {exc}"
                )

                self.last_results = []

                return self.snapshot()

            # --------------------------------------------------
            # NORMALIZAÇÃO
            # --------------------------------------------------

            (
                status,
                error,
                results,
            ) = self._normalize_response(
                response
            )

            self.last_status = status

            self.last_error = error

            self.last_results = list(
                results
            )

            # --------------------------------------------------
            # INVALID QUERY
            # --------------------------------------------------

            if (
                status
                == self.STATUS_INVALID_QUERY
            ):

                return self.snapshot()

            # --------------------------------------------------
            # PROVIDER ERROR
            # --------------------------------------------------

            if (
                status
                == self.STATUS_PROVIDER_ERROR
            ):

                return self.snapshot()

            # --------------------------------------------------
            # UNAVAILABLE
            # --------------------------------------------------

            if (
                status
                == self.STATUS_UNAVAILABLE
            ):

                return self.snapshot()

            # --------------------------------------------------
            # FOUND
            # ------------------------------------------------------

            if (
                status
                == self.STATUS_FOUND
            ):

                if results:

                    return self.snapshot()

                # FOUND sem candidatos.
                # Continua para próxima query.

                continue

            # --------------------------------------------------
            # NOT FOUND
            # --------------------------------------------------

            if (
                status
                == self.STATUS_NOT_FOUND
            ):

                continue

            # --------------------------------------------------
            # STATUS DESCONHECIDO
            # --------------------------------------------------

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                "Status de discovery "
                "desconhecido."
            )

            self.last_results = []

            return self.snapshot()

        # ------------------------------------------------------
        # NENHUMA QUERY PRODUZIU RESULTADO
        # ------------------------------------------------------

        self.last_status = (
            self.STATUS_NOT_FOUND
        )

        self.last_results = []

        self.last_error = (
            "Nenhum candidato encontrado "
            "nas consultas semânticas."
        )

        return self.snapshot()

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
            "queries": list(
                self.last_queries
            ),
            "query": (
                self.last_query
            ),
            "status": (
                self.last_status
            ),
            "error": (
                self.last_error
            ),
            "results": list(
                self.last_results
            ),
            "candidate_count": len(
                self.last_results
            ),
        }