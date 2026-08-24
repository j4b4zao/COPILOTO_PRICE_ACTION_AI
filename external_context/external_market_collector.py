"""
external_context/external_market_collector.py

External Market Collector

RC2

Responsabilidade:

- receber dados externos;
- converter valores;
- validar os dados;
- preencher ExternalMarketState.

Não:

- gera BUY;
- gera SELL;
- calcula Strategy;
- calcula Score;
- aprova operações;
- interpreta RISK_ON/RISK_OFF.
"""

from external_context.external_market_state import (
    ExternalMarketState,
)


class ExternalMarketCollector:

    NAME = "ExternalMarketCollector"

    VERSION = "RC2"

    ENABLED = True

    # ==========================================================
    # MERCADOS SUPORTADOS
    # ==========================================================

    MARKETS = (
        "US500",
        "NASDAQ",
        "DXY",
        "VIX",
        "US10Y",
        "OIL",
        "GOLD",
    )

    # ==========================================================
    # COLETAR
    # ==========================================================

    def coletar(
        self,
        data: dict,
    ) -> ExternalMarketState:

        state = ExternalMarketState()

        # ------------------------------------------------------
        # PROTEÇÃO CONTRA DADOS INVÁLIDOS
        # ------------------------------------------------------

        if not isinstance(data, dict):

            state.add_reason(
                "Dados de mercado externos inválidos."
            )

            return state

        # ======================================================
        # PREÇOS
        # ======================================================

        state.us500 = self._to_float(
            data.get("us500")
        )

        state.nasdaq = self._to_float(
            data.get("nasdaq")
        )

        state.dxy = self._to_float(
            data.get("dxy")
        )

        state.vix = self._to_float(
            data.get("vix")
        )

        state.us10y = self._to_float(
            data.get("us10y")
        )

        state.oil = self._to_float(
            data.get("oil")
        )

        state.gold = self._to_float(
            data.get("gold")
        )

        # ======================================================
        # VARIAÇÕES
        # ======================================================

        state.us500_change = self._to_float(
            data.get("us500_change")
        )

        state.nasdaq_change = self._to_float(
            data.get("nasdaq_change")
        )

        state.dxy_change = self._to_float(
            data.get("dxy_change")
        )

        state.vix_change = self._to_float(
            data.get("vix_change")
        )

        state.us10y_change = self._to_float(
            data.get("us10y_change")
        )

        state.oil_change = self._to_float(
            data.get("oil_change")
        )

        state.gold_change = self._to_float(
            data.get("gold_change")
        )

        # ======================================================
        # TIMESTAMP
        # ======================================================

        timestamp = data.get(
            "timestamp",
            "",
        )

        if timestamp is None:

            timestamp = ""

        state.timestamp = str(
            timestamp
        )

        # ======================================================
        # VALIDAÇÃO
        # ======================================================

        errors = self._validate(
            state
        )

        if errors:

            for error in errors:

                state.add_reason(
                    error
                )

            return state

        # ======================================================
        # ESTADO VÁLIDO
        # ======================================================

        state.valid = True

        state.add_reason(
            "Dados externos coletados com sucesso."
        )

        return state

    # ==========================================================
    # CONVERSÃO
    # ==========================================================

    @staticmethod
    def _to_float(
        value,
    ) -> float:

        if value is None:

            return 0.0

        try:

            return float(value)

        except (
            TypeError,
            ValueError,
        ):

            return 0.0

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    @staticmethod
    def _validate(
        state: ExternalMarketState,
    ) -> list[str]:

        errors = []

        required_prices = {
            "US500": state.us500,
            "NASDAQ": state.nasdaq,
            "DXY": state.dxy,
            "VIX": state.vix,
            "US10Y": state.us10y,
            "OIL": state.oil,
            "GOLD": state.gold,
        }

        for name, value in required_prices.items():

            if value <= 0:

                errors.append(
                    f"{name} inválido."
                )

        return errors