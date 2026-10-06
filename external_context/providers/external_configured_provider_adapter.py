"""Identity-preserving adapter from canonical assets to a configured provider.

This adapter performs no network or environment work by itself. It delegates
fetch(provider_symbol) to an injected transport/provider and enriches successful
dict payloads with the validated provider identity from the offline manifest.
"""
from copy import deepcopy

from external_context.providers.external_provider_configuration_manifest import (
    ExternalProviderConfigurationManifest,
)


class ExternalConfiguredProviderAdapter:
    NAME = "ExternalConfiguredProviderAdapter"
    VERSION = "RC1"

    def __init__(self, manifest, transport):
        if not isinstance(manifest, ExternalProviderConfigurationManifest):
            raise TypeError("manifest must be ExternalProviderConfigurationManifest")
        if not callable(getattr(transport, "fetch", None)):
            raise TypeError("transport must expose fetch(provider_symbol)")
        self._provider_name = manifest.provider_name
        self._symbols = manifest.provider_symbols()
        self._transport = transport

    def fetch(self, internal_asset: str):
        if internal_asset not in self._symbols:
            raise KeyError(f"unconfigured external asset: {internal_asset}")

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
            raise ValueError("transport provider_symbol conflicts with validated manifest")
        if supplied_provider not in (None, self._provider_name):
            raise ValueError("transport provider_name conflicts with validated manifest")

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
        }
