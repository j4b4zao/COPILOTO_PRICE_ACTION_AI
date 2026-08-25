"""
external_context/external_market_collector.py

External Market Collector

<<<<<<< HEAD
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
=======
RC2.1 - PROVIDER CONTRACT

Responsabilidades:
- continuar aceitando snapshots já normalizados via coletar(data);
- opcionalmente coletar dados por provider injetável via collect();
- converter e validar dados para ExternalMarketState;
- permanecer independente do núcleo operacional WIN/WDO;
- nunca gerar BUY/SELL, Strategy, Score, Risk ou Decision.

Provider esperado:

    fetch(symbol: str) -> dict | None

Payload por símbolo:

    {
        "price": 123.45,
        "change": 0.67,
        "timestamp": "...",  # opcional
    }
"""

from external_context.external_market_state import ExternalMarketState
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1


class ExternalMarketCollector:

    NAME = "ExternalMarketCollector"
<<<<<<< HEAD

    VERSION = "RC2"

    ENABLED = True

    # ==========================================================
    # MERCADOS SUPORTADOS
    # ==========================================================

=======
    VERSION = "RC2.1-PROVIDER-CONTRACT"
    ENABLED = True

>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
    MARKETS = (
        "US500",
        "NASDAQ",
        "DXY",
        "VIX",
        "US10Y",
        "OIL",
        "GOLD",
    )

<<<<<<< HEAD
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
=======
    FIELD_TO_SYMBOL = {
        "us500": "US500",
        "nasdaq": "NASDAQ",
        "dxy": "DXY",
        "vix": "VIX",
        "us10y": "US10Y",
        "oil": "OIL",
        "gold": "GOLD",
    }

    REQUIRED_FOR_CONTEXT = (
        "us500",
        "nasdaq",
        "dxy",
        "vix",
    )

    def __init__(self, provider=None):
        if provider is not None and not callable(getattr(provider, "fetch", None)):
            raise TypeError("Provider externo deve expor fetch(symbol).")
        self.provider = provider

    def collect(self) -> ExternalMarketState:
        """Coleta por provider e normaliza para o contrato existente."""
        if self.provider is None:
            raise RuntimeError("ExternalMarketCollector não possui provider configurado.")

        data = {}
        timestamps = []

        for field, symbol in self.FIELD_TO_SYMBOL.items():
            payload = self.provider.fetch(symbol)
            normalized = self._normalize_provider_payload(payload)
            if normalized is None:
                continue

            price, change, timestamp = normalized
            data[field] = price
            data[f"{field}_change"] = change
            if timestamp:
                timestamps.append(timestamp)

        if timestamps:
            data["timestamp"] = max(timestamps)

        return self.coletar(data, require_all_markets=False)

    def coletar(self, data: dict, *, require_all_markets: bool = True) -> ExternalMarketState:
        """Mantém compatibilidade com o coletor RC2 baseado em dict."""
        state = ExternalMarketState()

        if not isinstance(data, dict):
            state.add_reason("Dados de mercado externos inválidos.")
            return state

        for field in self.FIELD_TO_SYMBOL:
            setattr(state, field, self._to_float(data.get(field)))
            setattr(state, f"{field}_change", self._to_float(data.get(f"{field}_change")))

        timestamp = data.get("timestamp", "")
        state.timestamp = "" if timestamp is None else str(timestamp)

        errors = self._validate(state, require_all_markets=require_all_markets, raw=data)
        if errors:
            for error in errors:
                state.add_reason(error)
            return state

        state.valid = True
        state.add_reason("Dados externos coletados com sucesso.")
        return state

    @staticmethod
    def _normalize_provider_payload(payload):
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("Provider externo deve retornar dict ou None.")
        if "price" not in payload or "change" not in payload:
            return None

        try:
            price = float(payload["price"])
            change = float(payload["change"])
        except (TypeError, ValueError):
            return None

        if price <= 0:
            return None

        return price, change, str(payload.get("timestamp", "") or "")

    @staticmethod
    def _to_float(value) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @classmethod
    def _validate(cls, state: ExternalMarketState, *, require_all_markets: bool, raw: dict) -> list[str]:
        errors = []
        fields = tuple(cls.FIELD_TO_SYMBOL) if require_all_markets else cls.REQUIRED_FOR_CONTEXT

        for field in fields:
            symbol = cls.FIELD_TO_SYMBOL[field]
            price = getattr(state, field)
            if field not in raw or price <= 0:
                errors.append(f"{symbol} inválido ou ausente.")

        return errors
>>>>>>> 35766f332590b98fe808b92785ab4018de1333d1
