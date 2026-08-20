"""
external_context/providers/symbol_mapper.py

Mapeamento de símbolos internos para símbolos
específicos do provider.

RC2.1

Responsabilidades:

- receber candidatos descobertos;
- validar o estado da descoberta;
- criar mapeamentos somente quando permitido;
- preservar motivo de indisponibilidade;
- detectar mapa incompleto;
- nunca selecionar automaticamente um candidato
  ambíguo.

Não:

- consulta API;
- coleta preços;
- calcula contexto;
- gera sinais.
"""


class SymbolMapper:

    NAME = "SymbolMapper"

    VERSION = "RC2.1"

    STATUS_FOUND = "FOUND"

    STATUS_NOT_FOUND = "NOT_FOUND"

    STATUS_UNAVAILABLE = "UNAVAILABLE"

    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"

    STATUS_INVALID_QUERY = "INVALID_QUERY"

    STATUS_MAPPED = "MAPPED"

    STATUS_UNMAPPED = "UNMAPPED"

    # ==========================================================
    # CONSTRUTOR
    # ==========================================================

    def __init__(
        self,
        internal_symbols: list[str] | tuple[str, ...] | None = None,
    ):

        self.internal_symbols = list(
            internal_symbols or []
        )

        self.mapping: dict[str, str | None] = {}

        self.status: dict[str, str] = {}

        self.reasons: dict[str, str] = {}

        self.metadata: dict[str, dict] = {}

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.mapping.clear()

        self.status.clear()

        self.reasons.clear()

        self.metadata.clear()

    # ==========================================================
    # ADICIONAR MAPEAMENTO
    # ==========================================================

    def add_mapping(
        self,
        internal_symbol: str,
        provider_symbol: str,
        *,
        status: str = STATUS_FOUND,
        metadata: dict | None = None,
    ) -> bool:

        internal_symbol = str(
            internal_symbol
        ).strip()

        provider_symbol = str(
            provider_symbol
        ).strip()

        if not internal_symbol:

            return False

        if not provider_symbol:

            return False

        if status != self.STATUS_FOUND:

            self.mapping[
                internal_symbol
            ] = None

            self.status[
                internal_symbol
            ] = status

            self.reasons[
                internal_symbol
            ] = (
                "Mapeamento não permitido "
                f"com status {status}."
            )

            if metadata:

                self.metadata[
                    internal_symbol
                ] = dict(metadata)

            return False

        self.mapping[
            internal_symbol
        ] = provider_symbol

        self.status[
            internal_symbol
        ] = self.STATUS_MAPPED

        self.reasons[
            internal_symbol
        ] = (
            "Símbolo mapeado com sucesso."
        )

        if metadata:

            self.metadata[
                internal_symbol
            ] = dict(metadata)

        return True

    # ==========================================================
    # PROCESSAR RESULTADO DA DISCOVERY
    # ==========================================================

    def process_discovery(
        self,
        internal_symbol: str,
        provider_symbol: str | None,
        discovery_status: str,
        *,
        reason: str = "",
        metadata: dict | None = None,
    ) -> bool:
        """
        Processa o resultado do Discovery.

        FOUND:
            cria o mapeamento.

        NOT_FOUND:
            mantém sem mapeamento.

        UNAVAILABLE:
            mantém sem mapeamento e preserva motivo.

        PROVIDER_ERROR:
            mantém sem mapeamento.

        INVALID_QUERY:
            mantém sem mapeamento.
        """

        internal_symbol = str(
            internal_symbol
        ).strip()

        if not internal_symbol:

            return False

        # ------------------------------------------------------
        # FOUND
        # ------------------------------------------------------

        if (
            discovery_status
            == self.STATUS_FOUND
        ):

            if not provider_symbol:

                self.mapping[
                    internal_symbol
                ] = None

                self.status[
                    internal_symbol
                ] = self.STATUS_NOT_FOUND

                self.reasons[
                    internal_symbol
                ] = (
                    "Discovery informou FOUND, "
                    "mas não forneceu símbolo."
                )

                return False

            return self.add_mapping(
                internal_symbol,
                provider_symbol,
                status=self.STATUS_FOUND,
                metadata=metadata,
            )

        # ------------------------------------------------------
        # OUTROS ESTADOS
        # ------------------------------------------------------

        self.mapping[
            internal_symbol
        ] = None

        self.status[
            internal_symbol
        ] = discovery_status

        if reason:

            self.reasons[
                internal_symbol
            ] = reason

        else:

            self.reasons[
                internal_symbol
            ] = (
                f"Mapeamento bloqueado: "
                f"{discovery_status}."
            )

        if metadata:

            self.metadata[
                internal_symbol
            ] = dict(metadata)

        return False

    # ==========================================================
    # MAPEAR VÁRIOS
    # ==========================================================

    def process_many(
        self,
        results: list[dict],
    ) -> dict[str, str | None]:

        for result in results:

            if not isinstance(
                result,
                dict,
            ):

                continue

            self.process_discovery(
                internal_symbol=result.get(
                    "internal_symbol",
                    "",
                ),
                provider_symbol=result.get(
                    "provider_symbol"
                ),
                discovery_status=result.get(
                    "status",
                    self.STATUS_PROVIDER_ERROR,
                ),
                reason=result.get(
                    "reason",
                    "",
                ),
                metadata=result.get(
                    "metadata"
                ),
            )

        return dict(
            self.mapping
        )

    # ==========================================================
    # GET
    # ==========================================================

    def get(
        self,
        internal_symbol: str,
    ) -> str | None:

        return self.mapping.get(
            internal_symbol
        )

    # ==========================================================
    # STATUS
    # ==========================================================

    def get_status(
        self,
        internal_symbol: str,
    ) -> str:

        return self.status.get(
            internal_symbol,
            self.STATUS_NOT_FOUND,
        )

    # ==========================================================
    # MOTIVO
    # ==========================================================

    def get_reason(
        self,
        internal_symbol: str,
    ) -> str:

        return self.reasons.get(
            internal_symbol,
            "",
        )

    # ==========================================================
    # METADATA
    # ==========================================================

    def get_metadata(
        self,
        internal_symbol: str,
    ) -> dict:

        return dict(
            self.metadata.get(
                internal_symbol,
                {},
            )
        )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(self) -> int:

        return len(
            [
                symbol
                for symbol, provider_symbol
                in self.mapping.items()
                if provider_symbol
            ]
        )

    # ==========================================================
    # MISSING
    # ==========================================================

    def missing(
        self,
    ) -> list[str]:

        return [
            symbol
            for symbol in self.internal_symbols
            if not self.mapping.get(
                symbol
            )
        ]

    # ==========================================================
    # COMPLETE
    # ==========================================================

    def is_complete(self) -> bool:

        if not self.internal_symbols:

            return False

        return not self.missing()

    # ==========================================================
    # INDISPONÍVEIS
    # ==========================================================

    def unavailable(
        self,
    ) -> list[str]:

        return [
            symbol
            for symbol, status
            in self.status.items()
            if status
            == self.STATUS_UNAVAILABLE
        ]

    # ==========================================================
    # ERROS DO PROVIDER
    # ==========================================================

    def provider_errors(
        self,
    ) -> list[str]:

        return [
            symbol
            for symbol, status
            in self.status.items()
            if status
            == self.STATUS_PROVIDER_ERROR
        ]

    # ==========================================================
    # EXPORT
    # ==========================================================

    def all(
        self,
    ) -> dict[str, str | None]:

        return dict(
            self.mapping
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
            "mapping": dict(
                self.mapping
            ),
            "status": dict(
                self.status
            ),
            "reasons": dict(
                self.reasons
            ),
            "metadata": {
                key: dict(value)
                for key, value
                in self.metadata.items()
            },
            "count": self.count(),
            "missing": self.missing(),
            "complete": self.is_complete(),
            "unavailable": self.unavailable(),
            "provider_errors": (
                self.provider_errors()
            ),
        }