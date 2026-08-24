"""
external_context/providers/provider_symbol_map.py

Mapa de símbolos internos para símbolos do provider.

RC2.1

Responsabilidades:

- armazenar símbolos validados;
- preservar status do mapeamento;
- preservar motivos de bloqueio;
- preservar metadata;
- permitir consulta rápida;
- fornecer snapshot do estado atual.

Não:

- consulta APIs;
- faz discovery;
- seleciona automaticamente símbolos;
- coleta preços.
"""


class ProviderSymbolMap:

    NAME = "ProviderSymbolMap"

    VERSION = "RC2.1"

    STATUS_MAPPED = "MAPPED"

    STATUS_NOT_FOUND = "NOT_FOUND"

    STATUS_UNAVAILABLE = "UNAVAILABLE"

    STATUS_PROVIDER_ERROR = "PROVIDER_ERROR"

    STATUS_INVALID_QUERY = "INVALID_QUERY"

    def __init__(
        self,
        provider_name: str,
    ):

        self.provider_name = str(
            provider_name
        ).strip()

        self._symbols: dict[
            str,
            str,
        ] = {}

        self._status: dict[
            str,
            str,
        ] = {}

        self._reasons: dict[
            str,
            str,
        ] = {}

        self._metadata: dict[
            str,
            dict,
        ] = {}

    # ==========================================================
    # SET SYMBOL
    # ==========================================================

    def set_symbol(
        self,
        internal_asset: str,
        provider_symbol: str,
    ) -> bool:

        internal_asset = str(
            internal_asset
        ).strip()

        provider_symbol = str(
            provider_symbol
        ).strip()

        if not internal_asset:

            return False

        if not provider_symbol:

            return False

        self._symbols[
            internal_asset
        ] = provider_symbol

        self._status[
            internal_asset
        ] = self.STATUS_MAPPED

        self._reasons[
            internal_asset
        ] = (
            "Símbolo mapeado com sucesso."
        )

        self._metadata.setdefault(
            internal_asset,
            {},
        )

        return True

    # ==========================================================
    # PROCESSAR MAPEAMENTO
    # ==========================================================

    def process(
        self,
        internal_asset: str,
        provider_symbol: str | None,
        status: str,
        *,
        reason: str = "",
        metadata: dict | None = None,
    ) -> bool:
        """
        Recebe um resultado do SymbolMapper.

        Apenas MAPPED entra no mapa operacional.

        UNAVAILABLE, NOT_FOUND, PROVIDER_ERROR
        e INVALID_QUERY são preservados como estado,
        mas não recebem símbolo operacional.
        """

        internal_asset = str(
            internal_asset
        ).strip()

        if not internal_asset:

            return False

        status = str(
            status
        ).strip().upper()

        # ------------------------------------------------------
        # MAPPED
        # ------------------------------------------------------

        if (
            status
            == self.STATUS_MAPPED
        ):

            if not provider_symbol:

                self._status[
                    internal_asset
                ] = self.STATUS_NOT_FOUND

                self._reasons[
                    internal_asset
                ] = (
                    "Status MAPPED sem "
                    "símbolo do provider."
                )

                return False

            result = self.set_symbol(
                internal_asset,
                provider_symbol,
            )

            if metadata:

                self._metadata[
                    internal_asset
                ] = dict(metadata)

            if reason:

                self._reasons[
                    internal_asset
                ] = reason

            return result

        # ------------------------------------------------------
        # ESTADO NÃO OPERACIONAL
        # ------------------------------------------------------

        self._symbols.pop(
            internal_asset,
            None,
        )

        self._status[
            internal_asset
        ] = status

        if reason:

            self._reasons[
                internal_asset
            ] = reason

        else:

            self._reasons[
                internal_asset
            ] = (
                f"Mapeamento não operacional: "
                f"{status}."
            )

        if metadata:

            self._metadata[
                internal_asset
            ] = dict(metadata)

        else:

            self._metadata.setdefault(
                internal_asset,
                {},
            )

        return False

    # ==========================================================
    # GET SYMBOL
    # ==========================================================

    def get_symbol(
        self,
        internal_asset: str,
    ) -> str | None:

        return self._symbols.get(
            internal_asset
        )

    # ==========================================================
    # HAS SYMBOL
    # ==========================================================

    def has_symbol(
        self,
        internal_asset: str,
    ) -> bool:

        return (
            internal_asset
            in self._symbols
        )

    # ==========================================================
    # GET STATUS
    # ==========================================================

    def get_status(
        self,
        internal_asset: str,
    ) -> str | None:

        return self._status.get(
            internal_asset
        )

    # ==========================================================
    # GET REASON
    # ==========================================================

    def get_reason(
        self,
        internal_asset: str,
    ) -> str:

        return self._reasons.get(
            internal_asset,
            "",
        )

    # ==========================================================
    # GET METADATA
    # ==========================================================

    def get_metadata(
        self,
        internal_asset: str,
    ) -> dict:

        return dict(
            self._metadata.get(
                internal_asset,
                {},
            )
        )

    # ==========================================================
    # ALL SYMBOLS
    # ==========================================================

    def all_symbols(
        self,
    ) -> dict[str, str]:

        return dict(
            self._symbols
        )

    # ==========================================================
    # ALL STATUS
    # ==========================================================

    def all_status(
        self,
    ) -> dict[str, str]:

        return dict(
            self._status
        )

    # ==========================================================
    # ALL REASONS
    # ==========================================================

    def all_reasons(
        self,
    ) -> dict[str, str]:

        return dict(
            self._reasons
        )

    # ==========================================================
    # COUNT
    # ==========================================================

    def count(self) -> int:

        return len(
            self._symbols
        )

    # ==========================================================
    # UNAVAILABLE
    # ==========================================================

    def unavailable(
        self,
    ) -> list[str]:

        return [
            asset
            for asset, status
            in self._status.items()
            if status
            == self.STATUS_UNAVAILABLE
        ]

    # ==========================================================
    # PROVIDER ERRORS
    # ==========================================================

    def provider_errors(
        self,
    ) -> list[str]:

        return [
            asset
            for asset, status
            in self._status.items()
            if status
            == self.STATUS_PROVIDER_ERROR
        ]

    # ==========================================================
    # MISSING
    # ==========================================================

    def missing(
        self,
        required_assets: list[str] | tuple[str, ...],
    ) -> list[str]:

        return [
            asset
            for asset in required_assets
            if asset not in self._symbols
        ]

    # ==========================================================
    # COMPLETE
    # ==========================================================

    def is_complete(
        self,
        required_assets: list[str] | tuple[str, ...],
    ) -> bool:

        required_assets = list(
            required_assets
        )

        if not required_assets:

            return False

        return not self.missing(
            required_assets
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
            "provider": self.provider_name,
            "symbols": dict(
                self._symbols
            ),
            "status": dict(
                self._status
            ),
            "reasons": dict(
                self._reasons
            ),
            "metadata": {
                key: dict(value)
                for key, value
                in self._metadata.items()
            },
            "count": self.count(),
            "unavailable": self.unavailable(),
            "provider_errors": (
                self.provider_errors()
            ),
        }

    # ==========================================================
    # CLEAR
    # ==========================================================

    def clear(
        self,
    ) -> None:

        self._symbols.clear()

        self._status.clear()

        self._reasons.clear()

        self._metadata.clear()