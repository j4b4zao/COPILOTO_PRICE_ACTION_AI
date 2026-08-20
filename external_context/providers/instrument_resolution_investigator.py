"""
external_context/providers/instrument_resolution_investigator.py

Investiga candidatos de instrumentos externos.

RC2.3

IMPORTANTE:

Este componente NÃO:

- cria mapeamento;
- altera ProviderSymbolMap;
- seleciona automaticamente um símbolo;
- alimenta o SymbolResolutionEngine;
- aceita ETF como Index;
- substitui o SemanticSymbolResolver.

Responsabilidade:

Registrar e organizar candidatos encontrados pelo
provider para investigação manual/controlada.

Fluxo:

query
  ↓
discovery
  ↓
candidatos
  ↓
investigação
  ↓
classificação informativa
"""

from external_context.providers.instrument_profiles import (
    InstrumentProfiles,
)


class InstrumentResolutionInvestigator:

    NAME = "InstrumentResolutionInvestigator"

    VERSION = "RC2.3"

    STATUS_FOUND = "FOUND"

    STATUS_NOT_FOUND = "NOT_FOUND"

    STATUS_UNAVAILABLE = "UNAVAILABLE"

    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"

    STATUS_INVALID_QUERY = "INVALID_QUERY"

    VERDICT_INDEX = "INDEX_CANDIDATE"

    VERDICT_ETF = "ETF_CANDIDATE"

    VERDICT_FUND = "FUND_CANDIDATE"

    VERDICT_FOREIGN = "FOREIGN_CANDIDATE"

    VERDICT_OTHER = "OTHER_CANDIDATE"

    VERDICT_REJECTED = "REJECTED"

    def __init__(
        self,
        discovery,
    ):

        self.discovery = discovery

        self.last_internal_symbol = ""

        self.last_query = ""

        self.last_status = ""

        self.last_error = ""

        self.last_candidates = []

        self.last_investigated = []

        self.last_queries = []

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.last_internal_symbol = ""

        self.last_query = ""

        self.last_status = ""

        self.last_error = ""

        self.last_candidates.clear()

        self.last_investigated.clear()

        self.last_queries.clear()

    # ==========================================================
    # PERFIL
    # ==========================================================

    def _get_profile(
        self,
        internal_symbol: str,
    ):

        return InstrumentProfiles.get(
            internal_symbol
        )

    # ==========================================================
    # CLASSIFICAR CANDIDATO
    # ==========================================================

    def _classify_candidate(
        self,
        candidate: dict,
        profile: dict | None,
    ) -> dict:

        item_type = str(
            candidate.get(
                "type",
                "",
            )
        ).strip()

        country = str(
            candidate.get(
                "country",
                "",
            )
        ).strip()

        name = str(
            candidate.get(
                "name",
                "",
            )
        ).strip()

        expected_types = []

        expected_countries = []

        if profile:

            expected_types = [
                str(item).strip()
                for item in profile.get(
                    "allowed_types",
                    [],
                )
            ]

            expected_countries = [
                str(item).strip()
                for item in profile.get(
                    "allowed_countries",
                    [],
                )
            ]

        type_ok = (
            not expected_types
            or item_type in expected_types
        )

        country_ok = (
            not expected_countries
            or country in expected_countries
        )

        if (
            type_ok
            and country_ok
            and item_type == "Index"
        ):

            verdict = (
                self.VERDICT_INDEX
            )

        elif item_type == "ETF":

            verdict = (
                self.VERDICT_ETF
            )

        elif item_type in (
            "Mutual Fund",
            "Fund",
        ):

            verdict = (
                self.VERDICT_FUND
            )

        elif (
            not country_ok
            and item_type == "Index"
        ):

            verdict = (
                self.VERDICT_FOREIGN
            )

        else:

            verdict = (
                self.VERDICT_OTHER
            )

        if not type_ok:

            acceptance = (
                "REJECTED"
            )

        elif not country_ok:

            acceptance = (
                "REJECTED"
            )

        elif verdict == self.VERDICT_INDEX:

            acceptance = (
                "POTENTIAL_INDEX"
            )

        else:

            acceptance = (
                "REVIEW"
            )

        return {
            "symbol": candidate.get(
                "symbol",
                "",
            ),
            "name": name,
            "type": item_type,
            "exchange": candidate.get(
                "exchange",
                "",
            ),
            "mic_code": candidate.get(
                "mic_code",
                "",
            ),
            "country": country,
            "currency": candidate.get(
                "currency",
                "",
            ),
            "verdict": verdict,
            "acceptance": acceptance,
            "type_compatible": type_ok,
            "country_compatible": country_ok,
        }

    # ==========================================================
    # INVESTIGAR
    # ==========================================================

    def investigate(
        self,
        internal_symbol: str,
        query: str | None = None,
    ) -> dict:

        self.clear()

        internal_symbol = str(
            internal_symbol
        ).strip().upper()

        self.last_internal_symbol = (
            internal_symbol
        )

        profile = self._get_profile(
            internal_symbol
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
        # CONSULTA
        # ------------------------------------------------------

        if query is not None:

            queries = [
                str(query).strip()
            ]

        else:

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
                self.STATUS_INVALID_QUERY
            )

            self.last_error = (
                "Nenhuma consulta "
                "disponível."
            )

            return self.snapshot()

        # ------------------------------------------------------
        # EXECUTAR CONSULTAS
        # ------------------------------------------------------

        for current_query in queries:

            current_query = str(
                current_query
            ).strip()

            if not current_query:

                continue

            self.last_query = (
                current_query
            )

            try:

                response = (
                    self.discovery.search(
                        current_query
                    )
                )

            except Exception as exc:

                self.last_status = (
                    self.STATUS_PROVIDER_ERROR
                )

                self.last_error = (
                    f"Erro no discovery: "
                    f"{exc}"
                )

                return self.snapshot()

            # --------------------------------------------------
            # NORMALIZAR LISTA
            # --------------------------------------------------

            if not isinstance(
                response,
                list,
            ):

                self.last_status = (
                    self.STATUS_PROVIDER_ERROR
                )

                self.last_error = (
                    "Resposta do discovery "
                    "inválida."
                )

                return self.snapshot()

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

            self.last_status = status

            self.last_error = error

            self.last_candidates = [
                item
                for item in response
                if isinstance(
                    item,
                    dict,
                )
            ]

            # --------------------------------------------------
            # STATUS
            # --------------------------------------------------

            if status == self.STATUS_FOUND:

                if self.last_candidates:

                    self.last_investigated = [
                        self._classify_candidate(
                            candidate,
                            profile,
                        )
                        for candidate
                        in self.last_candidates
                    ]

                    return self.snapshot()

                continue

            if status == self.STATUS_NOT_FOUND:

                continue

            if status == self.STATUS_UNAVAILABLE:

                return self.snapshot()

            if status == self.STATUS_PROVIDER_ERROR:

                return self.snapshot()

            if status == self.STATUS_INVALID_QUERY:

                return self.snapshot()

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

            return self.snapshot()

        # ------------------------------------------------------
        # NADA ENCONTRADO
        # ------------------------------------------------------

        self.last_status = (
            self.STATUS_NOT_FOUND
        )

        self.last_candidates = []

        self.last_investigated = []

        if not self.last_error:

            self.last_error = (
                "Nenhum candidato encontrado "
                "nas consultas."
            )

        return self.snapshot()

    # ==========================================================
    # INDEX CANDIDATES
    # ==========================================================

    def index_candidates(
        self,
    ) -> list[dict]:

        return [
            item
            for item
            in self.last_investigated
            if item.get(
                "verdict"
            )
            == self.VERDICT_INDEX
        ]

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict:

        index_candidates = (
            self.index_candidates()
        )

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
            "candidate_count": len(
                self.last_candidates
            ),
            "investigated_count": len(
                self.last_investigated
            ),
            "index_candidates": list(
                index_candidates
            ),
            "investigated": list(
                self.last_investigated
            ),
        }