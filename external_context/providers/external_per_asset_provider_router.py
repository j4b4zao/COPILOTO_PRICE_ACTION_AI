"""Per-asset routing provider for the external observational layer.

The router owns no network, credentials, clocks, discovery, cache, mappings or
trading decisions. Each canonical asset is explicitly bound by the caller to an
injected provider exposing fetch(internal_asset).

Partial routing is allowed so provider availability can be evaluated without
pretending that the seven-asset external context is complete.
"""
from copy import deepcopy

from external_context.external_market_collector import ExternalMarketCollector


class ExternalPerAssetProviderRouter:
    NAME = "ExternalPerAssetProviderRouter"
    VERSION = "RC1"

    def __init__(self, routes: dict):
        if not isinstance(routes, dict):
            raise TypeError("routes must be a dict")

        canonical = set(ExternalMarketCollector.MARKETS)
        extras = set(routes).difference(canonical)
        if extras:
            raise ValueError("unexpected external assets in routes")

        validated = {}
        for asset, provider in routes.items():
            if not callable(getattr(provider, "fetch", None)):
                raise TypeError(f"provider for {asset} must expose fetch(internal_asset)")
            validated[asset] = provider
        self._routes = dict(validated)

    def fetch(self, internal_asset: str):
        if internal_asset not in ExternalMarketCollector.MARKETS:
            raise KeyError(f"unknown external asset: {internal_asset}")

        provider = self._routes.get(internal_asset)
        if provider is None:
            return None

        payload = provider.fetch(internal_asset)
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise TypeError("routed provider must return dict or None")

        enriched = deepcopy(payload)
        supplied_asset = enriched.get("internal_asset")
        if supplied_asset not in (None, internal_asset):
            raise ValueError("routed provider internal_asset conflicts with requested asset")
        enriched["internal_asset"] = internal_asset
        return enriched

    def snapshot(self):
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "routes": {
                asset: {
                    "provider_type": type(provider).__name__,
                    "configured": True,
                }
                for asset, provider in self._routes.items()
            },
            "configured_assets": tuple(
                asset for asset in ExternalMarketCollector.MARKETS if asset in self._routes
            ),
            "missing_assets": tuple(
                asset for asset in ExternalMarketCollector.MARKETS if asset not in self._routes
            ),
            "complete": len(self._routes) == len(ExternalMarketCollector.MARKETS),
            "observational_only": True,
            "operational_influence_allowed": False,
        }
