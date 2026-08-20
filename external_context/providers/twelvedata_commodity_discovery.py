"""
external_context/providers/twelvedata_commodity_discovery.py

Twelve Data Commodity Discovery
RC2.3

Responsabilidade:

    Descobrir commodities através do endpoint
    específico /commodities da Twelve Data.

Não é responsabilidade desta classe:

    - resolver símbolos arbitrariamente;
    - alterar mapas;
    - selecionar ETFs;
    - selecionar warrants;
    - misturar commodities com symbol_search.

Exemplos conhecidos:

    OIL  -> WTI/USD
    GOLD -> XAU/USD
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class TwelveDataCommodityDiscovery:
    """
    Discovery específico para commodities da Twelve Data.
    """

    NAME = "TwelveDataCommodityDiscovery"
    VERSION = "RC2.3"

    BASE_URL = (
        "https://api.twelvedata.com/commodities"
    )

    PROFILES: dict[str, dict[str, Any]] = {

        "OIL": {
            "keywords": [
                "WTI",
                "CRUDE OIL",
            ],
            "preferred_symbols": [
                "WTI/USD",
            ],
            "category": "Energy Resource",
        },

        "GOLD": {
            "keywords": [
                "GOLD",
            ],
            "preferred_symbols": [
                "XAU/USD",
            ],
            "category": "Precious Metal",
        },
    }

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = 15,
    ) -> None:

        self.api_key = (
            api_key
            or os.getenv(
                "TWELVE_DATA_API_KEY"
            )
        )

        self.timeout = timeout

        self.last_status = ""
        self.last_error = ""
        self.last_query = ""
        self.last_results: list[
            dict[str, Any]
        ] = []

    # ==========================================================
    # METADATA
    # ==========================================================

    def snapshot(self) -> dict[str, Any]:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "last_query": self.last_query,
            "result_count": len(
                self.last_results
            ),
        }

    # ==========================================================
    # PERFIL
    # ==========================================================

    @classmethod
    def profile(
        cls,
        internal_symbol: str,
    ) -> dict[str, Any] | None:

        return cls.PROFILES.get(
            internal_symbol.upper()
        )

    # ==========================================================
    # HTTP
    # ==========================================================

    def _request(
        self,
    ) -> tuple[int | None, str]:

        if not self.api_key:

            self.last_status = (
                "PROVIDER_ERROR"
            )

            self.last_error = (
                "TWELVE_DATA_API_KEY "
                "não configurada."
            )

            return None, ""

        params = urlencode(
            {
                "apikey": self.api_key,
            }
        )

        url = (
            f"{self.BASE_URL}?{params}"
        )

        request = Request(
            url,
            headers={
                "User-Agent":
                    "COPILOTO_PRICE_ACTION_AI"
            },
            method="GET",
        )

        try:

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                body = (
                    response
                    .read()
                    .decode("utf-8")
                )

                return response.status, body

        except HTTPError as exc:

            try:

                body = (
                    exc
                    .read()
                    .decode("utf-8")
                )

            except Exception:

                body = ""

            return exc.code, body

        except URLError as exc:

            self.last_status = (
                "PROVIDER_ERROR"
            )

            self.last_error = (
                f"Erro de conexão: {exc}"
            )

            return None, ""

        except Exception as exc:

            self.last_status = (
                "PROVIDER_ERROR"
            )

            self.last_error = (
                f"Erro inesperado: {exc}"
            )

            return None, ""

    # ==========================================================
    # FETCH
    # ==========================================================

    def fetch(
        self,
    ) -> list[dict[str, Any]]:

        status_code, body = (
            self._request()
        )

        if status_code != 200:

            if (
                status_code is not None
                and not self.last_error
            ):

                self.last_status = (
                    "PROVIDER_ERROR"
                )

                self.last_error = (
                    f"HTTP {status_code}: "
                    f"{body}"
                )

            self.last_results = []

            return []

        try:

            payload = json.loads(
                body
            )

        except Exception as exc:

            self.last_status = (
                "PROVIDER_ERROR"
            )

            self.last_error = (
                f"JSON inválido: {exc}"
            )

            self.last_results = []

            return []

        if not isinstance(
            payload,
            dict,
        ):

            self.last_status = (
                "PROVIDER_ERROR"
            )

            self.last_error = (
                "Resposta do provider "
                "inválida."
            )

            self.last_results = []

            return []

        data = payload.get(
            "data"
        )

        if not isinstance(
            data,
            list,
        ):

            self.last_status = (
                "PROVIDER_ERROR"
            )

            self.last_error = (
                "Campo 'data' inválido "
                "na resposta."
            )

            self.last_results = []

            return []

        results = []

        for item in data:

            if isinstance(
                item,
                dict,
            ):

                results.append(
                    dict(item)
                )

        self.last_results = results

        self.last_status = (
            "FOUND"
            if results
            else "NOT_FOUND"
        )

        self.last_error = ""

        return results

    # ==========================================================
    # NORMALIZAÇÃO
    # ==========================================================

    @staticmethod
    def _text(
        value: Any,
    ) -> str:

        if value is None:

            return ""

        return str(
            value
        ).strip().upper()

    # ==========================================================
    # MATCH INDIVIDUAL
    # ==========================================================

    def _matches_profile(
        self,
        internal_symbol: str,
        candidate: dict[str, Any],
    ) -> bool:

        profile = self.profile(
            internal_symbol
        )

        if profile is None:

            return False

        symbol = self._text(
            candidate.get(
                "symbol"
            )
        )

        name = self._text(
            candidate.get(
                "name"
            )
        )

        category = self._text(
            candidate.get(
                "category"
            )
        )

        expected_category = (
            self._text(
                profile.get(
                    "category"
                )
            )
        )

        # ------------------------------------------------------
        # CATEGORIA OBRIGATÓRIA
        # ------------------------------------------------------

        if (
            expected_category
            and category
            != expected_category
        ):

            return False

        # ------------------------------------------------------
        # SÍMBOLO PREFERENCIAL
        #
        # IMPORTANTE:
        # O símbolo preferencial não deve ser apenas
        # mais um critério semântico.
        #
        # Ele representa o instrumento exato que
        # queremos para aquele perfil.
        # ------------------------------------------------------

        preferred_symbols = [
            self._text(value)
            for value in profile.get(
                "preferred_symbols",
                [],
            )
        ]

        if preferred_symbols:

            return (
                symbol
                in preferred_symbols
            )

        # ------------------------------------------------------
        # FALLBACK SEMÂNTICO
        #
        # Só será utilizado para perfis que não
        # possuam símbolo preferencial.
        # ------------------------------------------------------

        keywords = [
            self._text(value)
            for value in profile.get(
                "keywords",
                [],
            )
        ]

        text = (
            f"{symbol} "
            f"{name} "
            f"{category}"
        )

        return any(
            keyword in text
            for keyword in keywords
        )

    # ==========================================================
    # DISCOVERY
    # ==========================================================

    def discover(
        self,
        internal_symbol: str,
    ) -> dict[str, Any]:

        self.last_query = (
            internal_symbol
        )

        self.last_status = ""
        self.last_error = ""
        self.last_results = []

        internal_symbol = (
            self._text(
                internal_symbol
            )
        )

        # ------------------------------------------------------
        # QUERY VAZIA
        # ------------------------------------------------------

        if not internal_symbol:

            self.last_status = (
                "INVALID_QUERY"
            )

            self.last_error = (
                "Símbolo interno vazio."
            )

            return {
                "name": self.NAME,
                "version": self.VERSION,
                "internal_symbol": "",
                "status": (
                    "INVALID_QUERY"
                ),
                "error": self.last_error,
                "results": [],
                "candidate_count": 0,
            }

        # ------------------------------------------------------
        # PERFIL DESCONHECIDO
        # ------------------------------------------------------

        if self.profile(
            internal_symbol
        ) is None:

            self.last_status = (
                "NOT_FOUND"
            )

            self.last_error = (
                "Perfil de commodity "
                "não configurado."
            )

            return {
                "name": self.NAME,
                "version": self.VERSION,
                "internal_symbol": (
                    internal_symbol
                ),
                "status": "NOT_FOUND",
                "error": self.last_error,
                "results": [],
                "candidate_count": 0,
            }

        # ------------------------------------------------------
        # FETCH
        # ------------------------------------------------------

        results = self.fetch()

        if (
            self.last_status
            == "PROVIDER_ERROR"
        ):

            return {
                "name": self.NAME,
                "version": self.VERSION,
                "internal_symbol": (
                    internal_symbol
                ),
                "status": (
                    "PROVIDER_ERROR"
                ),
                "error": self.last_error,
                "results": [],
                "candidate_count": 0,
            }

        # ------------------------------------------------------
        # MATCH
        # ------------------------------------------------------

        candidates = []

        for candidate in results:

            if self._matches_profile(
                internal_symbol,
                candidate,
            ):

                candidates.append(
                    candidate
                )

        # ------------------------------------------------------
        # NENHUM CANDIDATO
        # ------------------------------------------------------

        if not candidates:

            self.last_status = (
                "NOT_FOUND"
            )

            self.last_error = (
                "Nenhuma commodity "
                "compatível encontrada."
            )

            return {
                "name": self.NAME,
                "version": self.VERSION,
                "internal_symbol": (
                    internal_symbol
                ),
                "status": "NOT_FOUND",
                "error": self.last_error,
                "results": [],
                "candidate_count": 0,
            }

        # ------------------------------------------------------
        # FOUND
        # ------------------------------------------------------

        self.last_status = "FOUND"
        self.last_error = ""

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "internal_symbol": (
                internal_symbol
            ),
            "status": "FOUND",
            "error": "",
            "results": candidates,
            "candidate_count": len(
                candidates
            ),
        }

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.last_status = ""
        self.last_error = ""
        self.last_query = ""
        self.last_results = []