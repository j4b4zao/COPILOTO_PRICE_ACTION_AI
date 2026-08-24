"""
external_context/providers/symbol_resolution_engine.py

Orquestrador da resolução de símbolos.

RC2.2

Fluxo:

Discovery
    ↓
SymbolMapper
    ↓
ProviderSymbolMap
    ↓
ResolutionResult

Estados:

MAPPED
UNRESOLVED
AMBIGUOUS
NOT_FOUND
UNAVAILABLE
PROVIDER_ERROR
INVALID_QUERY

Regra operacional:

somente MAPPED pode resultar em:

    resolved = True

Todos os demais estados permanecem bloqueados.
"""


from dataclasses import dataclass, field

from external_context.providers.symbol_mapper import (
    SymbolMapper,
)

from external_context.providers.provider_symbol_map import (
    ProviderSymbolMap,
)


@dataclass(slots=True)
class SymbolResolutionResult:

    internal_symbol: str = ""

    candidate_symbol: str | None = None

    mapped_symbol: str | None = None

    discovery_status: str = ""

    mapper_status: str = ""

    final_status: str = ""

    resolved: bool = False

    reason: str = ""

    metadata: dict = field(
        default_factory=dict
    )

    def clear(self) -> None:

        self.internal_symbol = ""

        self.candidate_symbol = None

        self.mapped_symbol = None

        self.discovery_status = ""

        self.mapper_status = ""

        self.final_status = ""

        self.resolved = False

        self.reason = ""

        self.metadata.clear()


class SymbolResolutionEngine:

    NAME = "SymbolResolutionEngine"

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
        provider_name: str,
        required_symbols: list[str] | tuple[str, ...],
    ):

        self.provider_name = str(
            provider_name
        ).strip()

        self.required_symbols = list(
            required_symbols
        )

        self.mapper = SymbolMapper(
            self.required_symbols
        )

        self.symbol_map = ProviderSymbolMap(
            self.provider_name
        )

        self.results: dict[
            str,
            SymbolResolutionResult,
        ] = {}

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(self) -> None:

        self.mapper.clear()

        self.symbol_map.clear()

        self.results.clear()

    # ==========================================================
    # RESOLVE
    # ==========================================================

    def resolve(
        self,
        *,
        internal_symbol: str,
        provider_symbol: str | None,
        discovery_status: str,
        reason: str = "",
        metadata: dict | None = None,
    ) -> SymbolResolutionResult:
        """
        Processa um resultado de Discovery.

        Somente MAPPED pode gerar resolved=True.

        UNRESOLVED e AMBIGUOUS são estados válidos
        de bloqueio e não devem ser tratados como
        erro de provider.
        """

        internal_symbol = str(
            internal_symbol
        ).strip()

        discovery_status = str(
            discovery_status
        ).strip().upper()

        metadata = dict(
            metadata or {}
        )

        # ------------------------------------------------------
        # NORMALIZAÇÃO
        # ------------------------------------------------------

        if not internal_symbol:

            discovery_status = (
                self.STATUS_INVALID_QUERY
            )

            provider_symbol = None

            if not reason:

                reason = (
                    "Símbolo interno vazio."
                )

        # ------------------------------------------------------
        # ESTADOS DE BLOQUEIO SEM MAPEAMENTO
        # ------------------------------------------------------

        blocked_statuses = {
            self.STATUS_UNRESOLVED,
            self.STATUS_AMBIGUOUS,
            self.STATUS_NOT_FOUND,
            self.STATUS_UNAVAILABLE,
            self.STATUS_PROVIDER_ERROR,
            self.STATUS_INVALID_QUERY,
        }

        if (
            discovery_status
            in blocked_statuses
        ):

            provider_symbol = None

            self.symbol_map.process(
                internal_asset=internal_symbol,
                provider_symbol=None,
                status=discovery_status,
                reason=reason,
                metadata=metadata,
            )

            result = SymbolResolutionResult()

            result.internal_symbol = (
                internal_symbol
            )

            result.candidate_symbol = (
                metadata.get(
                    "candidate"
                )
                if isinstance(
                    metadata.get(
                        "candidate"
                    ),
                    str,
                )
                else None
            )

            # Para UNAVAILABLE do caso SPX,
            # o candidato pode estar em metadata.
            if (
                result.candidate_symbol
                is None
            ):

                result.candidate_symbol = (
                    metadata.get(
                        "candidate_symbol"
                    )
                )

            result.mapped_symbol = None

            result.discovery_status = (
                discovery_status
            )

            result.mapper_status = (
                discovery_status
            )

            result.final_status = (
                discovery_status
            )

            result.resolved = False

            result.reason = (
                reason
            )

            result.metadata = (
                self.symbol_map.get_metadata(
                    internal_symbol
                )
            )

            self.results[
                internal_symbol
            ] = result

            return result

        # ------------------------------------------------------
        # MAPPED
        # ------------------------------------------------------

        if (
            discovery_status
            == self.STATUS_MAPPED
        ):

            if not provider_symbol:

                self.symbol_map.process(
                    internal_asset=internal_symbol,
                    provider_symbol=None,
                    status=self.STATUS_NOT_FOUND,
                    reason=(
                        "Status MAPPED sem "
                        "símbolo do provider."
                    ),
                    metadata=metadata,
                )

                result = (
                    SymbolResolutionResult()
                )

                result.internal_symbol = (
                    internal_symbol
                )

                result.candidate_symbol = None

                result.mapped_symbol = None

                result.discovery_status = (
                    self.STATUS_MAPPED
                )

                result.mapper_status = (
                    self.STATUS_NOT_FOUND
                )

                result.final_status = (
                    self.STATUS_NOT_FOUND
                )

                result.resolved = False

                result.reason = (
                    "Status MAPPED sem "
                    "símbolo do provider."
                )

                result.metadata = (
                    self.symbol_map.get_metadata(
                        internal_symbol
                    )
                )

                self.results[
                    internal_symbol
                ] = result

                return result

            # --------------------------------------------------
            # MAPPER
            # --------------------------------------------------

            mapper_result = (
                self.mapper.process_discovery(
                    internal_symbol=internal_symbol,
                    provider_symbol=provider_symbol,
                    discovery_status="FOUND",
                    reason=reason,
                    metadata=metadata,
                )
            )

            mapper_status = (
                self.mapper.get_status(
                    internal_symbol
                )
            )

            mapper_reason = (
                self.mapper.get_reason(
                    internal_symbol
                )
            )

            mapped_symbol = (
                self.mapper.get(
                    internal_symbol
                )
            )

            # --------------------------------------------------
            # PROVIDER SYMBOL MAP
            # --------------------------------------------------

            if mapper_result:

                self.symbol_map.process(
                    internal_asset=internal_symbol,
                    provider_symbol=mapped_symbol,
                    status=self.STATUS_MAPPED,
                    reason=(
                        mapper_reason
                        or reason
                        or "Símbolo mapeado com sucesso."
                    ),
                    metadata=metadata,
                )

            else:

                self.symbol_map.process(
                    internal_asset=internal_symbol,
                    provider_symbol=None,
                    status=(
                        mapper_status
                        or self.STATUS_NOT_FOUND
                    ),
                    reason=(
                        mapper_reason
                        or "Falha ao mapear símbolo."
                    ),
                    metadata=metadata,
                )

            final_status = (
                self.symbol_map.get_status(
                    internal_symbol
                )
                or mapper_status
                or self.STATUS_NOT_FOUND
            )

            final_symbol = (
                self.symbol_map.get_symbol(
                    internal_symbol
                )
            )

            result = (
                SymbolResolutionResult()
            )

            result.internal_symbol = (
                internal_symbol
            )

            result.candidate_symbol = (
                provider_symbol
            )

            result.mapped_symbol = (
                final_symbol
            )

            result.discovery_status = (
                self.STATUS_MAPPED
            )

            result.mapper_status = (
                mapper_status
            )

            result.final_status = (
                final_status
            )

            result.resolved = (
                final_status
                == self.STATUS_MAPPED
                and final_symbol
                is not None
            )

            result.reason = (
                self.symbol_map.get_reason(
                    internal_symbol
                )
                or mapper_reason
                or reason
            )

            result.metadata = (
                self.symbol_map.get_metadata(
                    internal_symbol
                )
            )

            self.results[
                internal_symbol
            ] = result

            return result

        # ------------------------------------------------------
        # STATUS DESCONHECIDO
        # ------------------------------------------------------

        self.symbol_map.process(
            internal_asset=internal_symbol,
            provider_symbol=None,
            status=self.STATUS_PROVIDER_ERROR,
            reason=(
                "Status de discovery desconhecido."
            ),
            metadata={
                **metadata,
                "discovery_status": (
                    discovery_status
                ),
            },
        )

        result = SymbolResolutionResult()

        result.internal_symbol = (
            internal_symbol
        )

        result.candidate_symbol = None

        result.mapped_symbol = None

        result.discovery_status = (
            discovery_status
        )

        result.mapper_status = (
            self.STATUS_PROVIDER_ERROR
        )

        result.final_status = (
            self.STATUS_PROVIDER_ERROR
        )

        result.resolved = False

        result.reason = (
            "Status de discovery desconhecido."
        )

        result.metadata = (
            self.symbol_map.get_metadata(
                internal_symbol
            )
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
        discoveries: list[dict],
    ) -> list[SymbolResolutionResult]:
        """
        Processa vários resultados.
        """

        results = []

        for discovery in discoveries:

            if not isinstance(
                discovery,
                dict,
            ):

                continue

            result = self.resolve(
                internal_symbol=discovery.get(
                    "internal_symbol",
                    "",
                ),
                provider_symbol=discovery.get(
                    "provider_symbol"
                ),
                discovery_status=discovery.get(
                    "status",
                    self.STATUS_PROVIDER_ERROR,
                ),
                reason=discovery.get(
                    "reason",
                    "",
                ),
                metadata=discovery.get(
                    "metadata"
                ),
            )

            results.append(
                result
            )

        return results

    # ==========================================================
    # GET RESULT
    # ==========================================================

    def get_result(
        self,
        internal_symbol: str,
    ) -> SymbolResolutionResult | None:

        return self.results.get(
            internal_symbol
        )

    # ==========================================================
    # RESOLVIDOS
    # ==========================================================

    def resolved_symbols(
        self,
    ) -> dict[str, str]:

        return self.symbol_map.all_symbols()

    # ==========================================================
    # INDISPONÍVEIS
    # ==========================================================

    def unavailable(
        self,
    ) -> list[str]:

        return self.symbol_map.unavailable()

    # ==========================================================
    # ERROS
    # ==========================================================

    def provider_errors(
        self,
    ) -> list[str]:

        return self.symbol_map.provider_errors()

    # ==========================================================
    # MISSING
    # ==========================================================

    def missing(
        self,
    ) -> list[str]:

        return self.symbol_map.missing(
            self.required_symbols
        )

    # ==========================================================
    # COMPLETE
    # ==========================================================

    def is_complete(
        self,
    ) -> bool:

        return self.symbol_map.is_complete(
            self.required_symbols
        )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(
        self,
    ) -> int:

        return self.symbol_map.count()

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(
        self,
    ) -> dict:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "provider": self.provider_name,
            "resolved": (
                self.resolved_symbols()
            ),
            "unavailable": (
                self.unavailable()
            ),
            "provider_errors": (
                self.provider_errors()
            ),
            "missing": (
                self.missing()
            ),
            "count": (
                self.count()
            ),
            "complete": (
                self.is_complete()
            ),
            "results": {
                symbol: {
                    "candidate": (
                        result.candidate_symbol
                    ),
                    "mapped": (
                        result.mapped_symbol
                    ),
                    "discovery_status": (
                        result.discovery_status
                    ),
                    "mapper_status": (
                        result.mapper_status
                    ),
                    "final_status": (
                        result.final_status
                    ),
                    "resolved": (
                        result.resolved
                    ),
                    "reason": (
                        result.reason
                    ),
                    "metadata": dict(
                        result.metadata
                    ),
                }
                for symbol, result
                in self.results.items()
            },
        }