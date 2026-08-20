"""
external_context/providers/twelvedata_symbol_discovery.py

Symbol Discovery para Twelve Data.

RC2.1

Responsabilidades:

- consultar /symbol_search;
- transformar a resposta da API;
- diferenciar:
    FOUND
    NOT_FOUND
    UNAVAILABLE
    PROVIDER_ERROR
    INVALID_QUERY;
- classificar candidatos;
- detectar ambiguidade;
- não selecionar automaticamente um instrumento.

Não:

- coleta preços;
- calcula contexto;
- gera sinais;
- gera BUY/SELL;
- grava automaticamente ProviderSymbolMap.
"""

import json
import os

from urllib.error import HTTPError
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request
from urllib.request import urlopen

from external_context.providers.symbol_discovery import (
    SymbolDiscovery,
)


class TwelveDataSymbolDiscovery(SymbolDiscovery):

    NAME = "TwelveDataSymbolDiscovery"

    VERSION = "RC2.1"

    BASE_URL = (
        "https://api.twelvedata.com"
    )

    STATUS_FOUND = "FOUND"

    STATUS_NOT_FOUND = "NOT_FOUND"

    STATUS_UNAVAILABLE = "UNAVAILABLE"

    STATUS_PROVIDER_ERROR = (
        "PROVIDER_ERROR"
    )

    STATUS_INVALID_QUERY = (
        "INVALID_QUERY"
    )

    # ==========================================================
    # CONSTRUTOR
    # ==========================================================

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 10.0,
    ):

        if api_key is None:

            api_key = os.getenv(
                "TWELVE_DATA_API_KEY",
                "",
            )

        self.api_key = str(
            api_key
        ).strip()

        self.timeout = float(
            timeout
        )

        self.last_status = (
            self.STATUS_NOT_FOUND
        )

        self.last_error = ""

    # ==========================================================
    # CLASSIFICAR ERRO DA API
    # ==========================================================

    @classmethod
    def classify_provider_error(
        cls,
        status_code: int | None,
        message: str = "",
    ) -> str:
        """
        Classifica erros retornados pela Twelve Data.

        Regras principais:

        401:
            problema de autenticação.

        403:
            acesso/permissão.

        429:
            limite de créditos/rate limit.

        Mensagem indicando plano superior:
            UNAVAILABLE.

        Outros:
            PROVIDER_ERROR.
        """

        text = str(
            message
        ).strip().lower()

        # ------------------------------------------------------
        # RECURSO DISPONÍVEL SOMENTE EM PLANO SUPERIOR
        # ------------------------------------------------------

        unavailable_terms = (
            "available starting with",
            "starting with the grow",
            "starting with the venture",
            "upgrade",
            "upgrading",
            "plan",
            "subscription",
        )

        if any(
            term in text
            for term in unavailable_terms
        ):

            return cls.STATUS_UNAVAILABLE

        # ------------------------------------------------------
        # AUTENTICAÇÃO
        # ------------------------------------------------------

        if status_code == 401:

            return cls.STATUS_PROVIDER_ERROR

        # ------------------------------------------------------
        # PERMISSÃO
        # ------------------------------------------------------

        if status_code == 403:

            return cls.STATUS_UNAVAILABLE

        # ------------------------------------------------------
        # RATE LIMIT
        # ------------------------------------------------------

        if status_code == 429:

            return cls.STATUS_PROVIDER_ERROR

        # ------------------------------------------------------
        # OUTROS
        # ------------------------------------------------------

        return cls.STATUS_PROVIDER_ERROR

    # ==========================================================
    # SEARCH
    # ==========================================================

    def search(
        self,
        query: str,
    ) -> list[dict]:

        query = str(
            query
        ).strip()

        self.last_error = ""

        # ------------------------------------------------------
        # QUERY INVÁLIDA
        # ------------------------------------------------------

        if not query:

            self.last_status = (
                self.STATUS_INVALID_QUERY
            )

            self.last_error = (
                "Consulta de símbolo vazia."
            )

            return []

        # ------------------------------------------------------
        # API KEY
        # ------------------------------------------------------

        if not self.api_key:

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                "TWELVE_DATA_API_KEY "
                "não configurada."
            )

            return []

        # ------------------------------------------------------
        # PARÂMETROS
        # ------------------------------------------------------

        params = {
            "symbol": query,
            "outputsize": 30,
            "apikey": self.api_key,
        }

        url = (
            f"{self.BASE_URL}/symbol_search?"
            f"{urlencode(params)}"
        )

        # ------------------------------------------------------
        # REQUEST
        # ------------------------------------------------------

        try:

            request = Request(
                url,
                headers={
                    "User-Agent":
                        "COPILOTO_PRICE_ACTION_AI/RC2.1"
                },
            )

            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                raw = response.read()

            payload = json.loads(
                raw.decode("utf-8")
            )

        except HTTPError as exc:

            try:

                body = exc.read().decode(
                    "utf-8"
                )

            except Exception:

                body = ""

            message = (
                body
                or str(exc.reason)
            )

            self.last_status = (
                self.classify_provider_error(
                    exc.code,
                    message,
                )
            )

            self.last_error = message

            return []

        except URLError as exc:

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                f"Erro de conexão: "
                f"{exc.reason}"
            )

            return []

        except TimeoutError:

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                "Timeout ao consultar "
                "Twelve Data."
            )

            return []

        except json.JSONDecodeError:

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                "Resposta da Twelve Data "
                "não contém JSON válido."
            )

            return []

        except Exception as exc:

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                f"Erro inesperado: {exc}"
            )

            return []

        # ------------------------------------------------------
        # PAYLOAD
        # ------------------------------------------------------

        if not isinstance(
            payload,
            dict,
        ):

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                "Resposta da API não é "
                "um objeto JSON."
            )

            return []

        # ------------------------------------------------------
        # ERRO DA API
        # ------------------------------------------------------

        if (
            payload.get("status")
            == "error"
        ):

            code = payload.get(
                "code"
            )

            message = str(
                payload.get(
                    "message",
                    "Erro retornado pela API.",
                )
            )

            self.last_status = (
                self.classify_provider_error(
                    code,
                    message,
                )
            )

            self.last_error = message

            return []

        # ------------------------------------------------------
        # DATA
        # ------------------------------------------------------

        data = payload.get(
            "data",
            [],
        )

        if not isinstance(
            data,
            list,
        ):

            self.last_status = (
                self.STATUS_PROVIDER_ERROR
            )

            self.last_error = (
                "Campo 'data' inválido."
            )

            return []

        # ------------------------------------------------------
        # NORMALIZAÇÃO
        # ------------------------------------------------------

        results = []

        for item in data:

            if not isinstance(
                item,
                dict,
            ):

                continue

            result = {
                "symbol": item.get(
                    "symbol",
                    "",
                ),
                "name": item.get(
                    "instrument_name",
                    "",
                ),
                "type": item.get(
                    "instrument_type",
                    "",
                ),
                "exchange": item.get(
                    "exchange",
                    "",
                ),
                "mic_code": item.get(
                    "mic_code",
                    "",
                ),
                "country": item.get(
                    "country",
                    "",
                ),
                "currency": item.get(
                    "currency",
                    "",
                ),
            }

            results.append(
                result
            )

        # ------------------------------------------------------
        # STATUS
        # ------------------------------------------------------

        if results:

            self.last_status = (
                self.STATUS_FOUND
            )

        else:

            self.last_status = (
                self.STATUS_NOT_FOUND
            )

        return results

    # ==========================================================
    # VALIDATE SYMBOL
    # ==========================================================

    def validate_symbol(
        self,
        symbol: str,
    ) -> bool:

        symbol = str(
            symbol
        ).strip()

        if not symbol:

            self.last_status = (
                self.STATUS_INVALID_QUERY
            )

            self.last_error = (
                "Símbolo vazio."
            )

            return False

        results = self.search(
            symbol
        )

        if (
            self.last_status
            != self.STATUS_FOUND
        ):

            return False

        target = symbol.upper()

        for result in results:

            candidate = str(
                result.get(
                    "symbol",
                    "",
                )
            ).upper()

            if candidate == target:

                return True

        self.last_status = (
            self.STATUS_NOT_FOUND
        )

        return False

    # ==========================================================
    # CLASSIFICAR CANDIDATOS
    # ==========================================================

    @staticmethod
    def classify_results(
        results: list[dict],
        *,
        expected_type: str | None = None,
        expected_country: str | None = None,
        expected_exchange: str | None = None,
        expected_name_terms: tuple[str, ...] = (),
    ) -> list[dict]:
        """
        Classifica candidatos.

        Não seleciona automaticamente.

        Adiciona:

            match_score
        """

        normalized_type = (
            str(expected_type)
            .strip()
            .lower()
            if expected_type
            else None
        )

        normalized_country = (
            str(expected_country)
            .strip()
            .lower()
            if expected_country
            else None
        )

        normalized_exchange = (
            str(expected_exchange)
            .strip()
            .lower()
            if expected_exchange
            else None
        )

        normalized_terms = tuple(
            str(term)
            .strip()
            .lower()
            for term in expected_name_terms
            if str(term).strip()
        )

        classified = []

        for item in results:

            if not isinstance(
                item,
                dict,
            ):

                continue

            score = 0

            item_type = str(
                item.get(
                    "type",
                    "",
                )
            ).strip().lower()

            item_country = str(
                item.get(
                    "country",
                    "",
                )
            ).strip().lower()

            item_exchange = str(
                item.get(
                    "exchange",
                    "",
                )
            ).strip().lower()

            item_name = str(
                item.get(
                    "name",
                    "",
                )
            ).strip().lower()

            if (
                normalized_type
                and item_type
                == normalized_type
            ):

                score += 50

            if (
                normalized_country
                and item_country
                == normalized_country
            ):

                score += 30

            if (
                normalized_exchange
                and item_exchange
                == normalized_exchange
            ):

                score += 20

            for term in normalized_terms:

                if term in item_name:

                    score += 10

            candidate = dict(
                item
            )

            candidate[
                "match_score"
            ] = score

            classified.append(
                candidate
            )

        classified.sort(
            key=lambda item: item.get(
                "match_score",
                0,
            ),
            reverse=True,
        )

        return classified

    # ==========================================================
    # MELHOR CANDIDATO
    # ==========================================================

    @staticmethod
    def best_candidate(
        results: list[dict],
    ) -> dict | None:

        if not results:

            return None

        return max(
            results,
            key=lambda item: item.get(
                "match_score",
                0,
            ),
        )

    # ==========================================================
    # AMBIGUIDADE
    # ==========================================================

    @staticmethod
    def is_ambiguous(
        results: list[dict],
    ) -> bool:

        if not results:

            return False

        highest = max(
            item.get(
                "match_score",
                0,
            )
            for item in results
        )

        best = [
            item
            for item in results
            if item.get(
                "match_score",
                0,
            )
            == highest
        ]

        return len(best) > 1