"""Offline manifest for a concrete external observational provider configuration.

The manifest validates provider identity evidence for every canonical external
asset. It performs no discovery, HTTP request, environment read, credential
lookup or provider construction. A later adapter may consume the detached
manifest only after this contract is validated.
"""
from copy import deepcopy
from dataclasses import dataclass

from external_context.external_market_collector import ExternalMarketCollector


@dataclass(frozen=True, slots=True)
class ExternalProviderAssetBinding:
    internal_asset: str
    provider_symbol: str
    status: str


@dataclass(frozen=True, slots=True)
class ExternalProviderConfigurationManifest:
    provider_name: str
    bindings: tuple[ExternalProviderAssetBinding, ...]
    symbol_map: dict

    NAME = "ExternalProviderConfigurationManifest"
    VERSION = "RC1"

    @classmethod
    def from_symbol_map(cls, snapshot: dict):
        if not isinstance(snapshot, dict):
            raise TypeError("snapshot must be ProviderSymbolMap.snapshot()")

        frozen = deepcopy(snapshot)
        provider_name = str(frozen.get("provider", "") or "").strip()
        symbols = frozen.get("symbols")
        statuses = frozen.get("status")

        if not provider_name:
            raise ValueError("provider identity is required")
        if not isinstance(symbols, dict) or not isinstance(statuses, dict):
            raise TypeError("invalid ProviderSymbolMap snapshot contract")

        bindings = []
        for internal_asset in ExternalMarketCollector.MARKETS:
            provider_symbol = symbols.get(internal_asset)
            status = statuses.get(internal_asset)

            if status != "MAPPED":
                raise ValueError(
                    f"{internal_asset} must be explicitly MAPPED before configuration"
                )
            if not isinstance(provider_symbol, str) or not provider_symbol.strip():
                raise ValueError(
                    f"{internal_asset} requires a non-empty provider symbol"
                )

            bindings.append(
                ExternalProviderAssetBinding(
                    internal_asset=internal_asset,
                    provider_symbol=provider_symbol.strip(),
                    status="MAPPED",
                )
            )

        extras = set(symbols).difference(ExternalMarketCollector.MARKETS)
        if extras:
            raise ValueError("unexpected external assets in provider symbol map")

        return cls(
            provider_name=provider_name,
            bindings=tuple(bindings),
            symbol_map=frozen,
        )

    def provider_symbols(self) -> dict[str, str]:
        return {
            binding.internal_asset: binding.provider_symbol
            for binding in self.bindings
        }

    def snapshot(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "provider": self.provider_name,
            "assets": [
                {
                    "internal_asset": binding.internal_asset,
                    "provider_symbol": binding.provider_symbol,
                    "status": binding.status,
                }
                for binding in self.bindings
            ],
            "count": len(self.bindings),
            "complete": len(self.bindings) == len(ExternalMarketCollector.MARKETS),
            "observational_only": True,
            "symbol_map": deepcopy(self.symbol_map),
        }
