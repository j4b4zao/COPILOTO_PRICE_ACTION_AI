"""
external_context/external_market_collector.py

External Market Collector

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

from copy import deepcopy
from datetime import datetime
from math import isfinite

from external_context.external_market_state import ExternalMarketState
from external_context._quote_values import normalize_quote_values
from external_context.external_observational_snapshot import ExternalObservationalSnapshot


class ExternalMarketCollector:

    NAME = "ExternalMarketCollector"
    VERSION = "RC2.2-OBSERVATIONAL-SNAPSHOT"
    ENABLED = True

    MARKETS = (
        "US500",
        "NASDAQ",
        "DXY",
        "VIX",
        "US10Y",
        "OIL",
        "GOLD",
    )

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

    def __init__(self, provider=None, *, preserve_quotes=False):
        if provider is not None and not callable(getattr(provider, "fetch", None)):
            raise TypeError("Provider externo deve expor fetch(symbol).")
        self.provider = provider
        self.preserve_quotes = preserve_quotes
        self.observational_snapshot = None
        self.observational_error = None

    def collect(self) -> ExternalMarketState:
        """Coleta por provider e normaliza para o contrato existente."""
        self.observational_snapshot = None
        self.observational_error = None
        if self.provider is None:
            raise RuntimeError("ExternalMarketCollector não possui provider configurado.")

        data = {}
        timestamps = []
        quotes = {}

        for field, symbol in self.FIELD_TO_SYMBOL.items():
            payload = self.provider.fetch(symbol)
            if self.preserve_quotes and self.observational_error is None:
                try:
                    quotes[symbol] = deepcopy(payload)
                except Exception as exc:
                    self.observational_error = type(exc).__name__
            normalized = self._normalize_provider_payload(payload)
            if normalized is None:
                continue

            price, change, timestamp = normalized
            data[field] = price
            data[f"{field}_change"] = change
            if timestamp:
                timestamps.append(timestamp)

        if timestamps:
            data["timestamp"] = self._latest_timestamp(timestamps)

        if self.preserve_quotes and self.observational_error is None:
            try:
                self.observational_snapshot = ExternalObservationalSnapshot.from_quotes(quotes)
            except Exception as exc:
                # Diagnostic unavailability never changes the official state.
                self.observational_error = type(exc).__name__

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
        values = normalize_quote_values(payload.get("price"), payload.get("change"))
        if values is None:
            return None

        price, change = values
        return price, change, str(payload.get("timestamp", "") or "")

    @staticmethod
    def _latest_timestamp(timestamps: list[str]) -> str:
        try:
            instants = [datetime.fromisoformat(value) for value in timestamps]
            if all(instant.utcoffset() is not None for instant in instants):
                return timestamps[max(range(len(instants)), key=instants.__getitem__)]
        except (ValueError, OverflowError):
            pass
        # Legacy providers may supply timestamps without timezone information.
        return max(timestamps)

    @staticmethod
    def _to_float(value) -> float:
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError, OverflowError):
            return float("nan")

    @classmethod
    def _validate(cls, state: ExternalMarketState, *, require_all_markets: bool, raw: dict) -> list[str]:
        errors = []
        fields = tuple(cls.FIELD_TO_SYMBOL) if require_all_markets else cls.REQUIRED_FOR_CONTEXT

        for field, symbol in cls.FIELD_TO_SYMBOL.items():
            price = getattr(state, field)
            invalid_price = isinstance(raw.get(field), bool) or not isfinite(price) or (
                (field in fields or field in raw) and price <= 0
            )
            if invalid_price:
                errors.append(f"{symbol} inválido ou ausente.")
                setattr(state, field, 0.0)
            change_field = f"{field}_change"
            if change_field in raw and (
                field not in raw
                or invalid_price
                or raw[change_field] is None
                or isinstance(raw[change_field], bool)
                or not isfinite(getattr(state, change_field))
            ):
                errors.append(f"Variação de {symbol} inválida.")
                setattr(state, change_field, 0.0)

        return errors
