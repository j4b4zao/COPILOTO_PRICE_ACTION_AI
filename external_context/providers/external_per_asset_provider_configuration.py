"""Partial provider binding for per-asset observational routing.

This contract deliberately does not weaken ExternalProviderConfigurationManifest,
which remains the complete single-provider/all-assets path. RC1 represents only
explicit, evidence-approved bindings for one provider and performs no network,
environment, discovery, clock, router construction, or operational integration.
"""
from copy import deepcopy
from dataclasses import dataclass

from external_context.external_market_collector import ExternalMarketCollector


@dataclass(frozen=True, slots=True)
class ExternalPerAssetProviderBinding:
    internal_asset: str
    provider_symbol: str


@dataclass(frozen=True, slots=True)
class ExternalPerAssetProviderConfiguration:
    provider_name: str
    bindings: tuple[ExternalPerAssetProviderBinding, ...]

    NAME = "ExternalPerAssetProviderConfiguration"
    VERSION = "RC1"

    @classmethod
    def create(cls, *, provider_name: str, symbols: dict[str, str]):
        name = str(provider_name or "").strip()
        if not name:
            raise ValueError("provider_name is required")
        if not isinstance(symbols, dict):
            raise TypeError("symbols must be a dict")
        if not symbols:
            raise ValueError("at least one explicit asset binding is required")

        canonical = set(ExternalMarketCollector.MARKETS)
        extras = set(symbols).difference(canonical)
        if extras:
            raise ValueError("unexpected external assets in symbols")

        bindings = []
        for asset in ExternalMarketCollector.MARKETS:
            if asset not in symbols:
                continue
            provider_symbol = symbols[asset]
            if not isinstance(provider_symbol, str) or not provider_symbol.strip():
                raise ValueError(f"{asset} requires a non-empty provider symbol")
            bindings.append(
                ExternalPerAssetProviderBinding(
                    internal_asset=asset,
                    provider_symbol=provider_symbol.strip(),
                )
            )
        return cls(provider_name=name, bindings=tuple(bindings))

    def provider_symbols(self) -> dict[str, str]:
        return {
            binding.internal_asset: binding.provider_symbol
            for binding in self.bindings
        }

    def snapshot(self) -> dict:
        symbols = self.provider_symbols()
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "provider": self.provider_name,
            "assets": [
                {
                    "internal_asset": binding.internal_asset,
                    "provider_symbol": binding.provider_symbol,
                    "status": "MAPPED",
                }
                for binding in self.bindings
            ],
            "configured_assets": tuple(
                asset for asset in ExternalMarketCollector.MARKETS if asset in symbols
            ),
            "missing_assets": tuple(
                asset for asset in ExternalMarketCollector.MARKETS if asset not in symbols
            ),
            "count": len(self.bindings),
            "complete": len(self.bindings) == len(ExternalMarketCollector.MARKETS),
            "observational_only": True,
            "operational_influence_allowed": False,
        }


class ExternalPartialConfiguredProviderAdapter:
    """Map configured canonical assets to provider symbols for one transport."""

    NAME = "ExternalPartialConfiguredProviderAdapter"
    VERSION = "RC1"

    def __init__(self, configuration, transport):
        if not isinstance(configuration, ExternalPerAssetProviderConfiguration):
            raise TypeError("configuration must be ExternalPerAssetProviderConfiguration")
        if not callable(getattr(transport, "fetch", None)):
            raise TypeError("transport must expose fetch(provider_symbol)")
        self._provider_name = configuration.provider_name
        self._symbols = configuration.provider_symbols()
        self._transport = transport

    def fetch(self, internal_asset: str):
        if internal_asset not in self._symbols:
            raise KeyError(f"unconfigured provider asset: {internal_asset}")

        provider_symbol = self._symbols[internal_asset]
        payload = self._transport.fetch(provider_symbol)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("configured provider transport must return dict or None")

        enriched = deepcopy(payload)
        supplied_symbol = enriched.get("provider_symbol")
        supplied_provider = enriched.get("provider_name")
        if supplied_symbol not in (None, provider_symbol):
            raise ValueError("transport provider_symbol conflicts with configured binding")
        if supplied_provider not in (None, self._provider_name):
            raise ValueError("transport provider_name conflicts with configured binding")
        enriched["provider_symbol"] = provider_symbol
        enriched["provider_name"] = self._provider_name
        return enriched

    def snapshot(self):
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "provider": self._provider_name,
            "symbols": dict(self._symbols),
            "observational_only": True,
            "operational_influence_allowed": False,
        }
