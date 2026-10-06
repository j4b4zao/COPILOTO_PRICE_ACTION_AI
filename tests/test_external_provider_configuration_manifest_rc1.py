"""RC1 acceptance for the offline external provider configuration manifest."""
from copy import deepcopy

import pytest

from external_context.external_market_collector import ExternalMarketCollector
from external_context.providers.external_provider_configuration_manifest import (
    ExternalProviderConfigurationManifest,
)


ASSETS = ExternalMarketCollector.MARKETS


def complete_map():
    return {
        "name": "ProviderSymbolMap",
        "version": "RC2.1",
        "provider": "controlled-provider",
        "symbols": {asset: f"P:{asset}" for asset in ASSETS},
        "status": {asset: "MAPPED" for asset in ASSETS},
        "reasons": {asset: "controlled" for asset in ASSETS},
        "metadata": {asset: {} for asset in ASSETS},
        "count": len(ASSETS),
        "unavailable": [],
        "provider_errors": [],
    }


def test_complete_explicit_map_builds_seven_asset_manifest():
    manifest = ExternalProviderConfigurationManifest.from_symbol_map(complete_map())

    assert manifest.provider_name == "controlled-provider"
    assert tuple(x.internal_asset for x in manifest.bindings) == ASSETS
    assert manifest.provider_symbols() == {
        asset: f"P:{asset}" for asset in ASSETS
    }
    assert manifest.snapshot()["complete"] is True
    assert manifest.snapshot()["observational_only"] is True


@pytest.mark.parametrize(
    "status",
    ["NOT_FOUND", "UNAVAILABLE", "PROVIDER_ERROR", "AMBIGUOUS", "UNRESOLVED", ""],
)
def test_any_non_mapped_required_asset_blocks_configuration(status):
    source = complete_map()
    source["status"]["DXY"] = status
    source["symbols"].pop("DXY", None)

    with pytest.raises(ValueError, match="DXY"):
        ExternalProviderConfigurationManifest.from_symbol_map(source)


def test_missing_required_asset_blocks_configuration():
    source = complete_map()
    source["symbols"].pop("VIX")
    source["status"].pop("VIX")

    with pytest.raises(ValueError, match="VIX"):
        ExternalProviderConfigurationManifest.from_symbol_map(source)


@pytest.mark.parametrize("bad", [None, "", "   "])
def test_missing_provider_identity_blocks_configuration(bad):
    source = complete_map()
    source["provider"] = bad

    with pytest.raises(ValueError, match="provider identity"):
        ExternalProviderConfigurationManifest.from_symbol_map(source)


def test_invalid_snapshot_shape_blocks_configuration():
    for bad in (None, [], "map", object()):
        with pytest.raises(TypeError):
            ExternalProviderConfigurationManifest.from_symbol_map(bad)

    source = complete_map()
    source["symbols"] = []
    with pytest.raises(TypeError):
        ExternalProviderConfigurationManifest.from_symbol_map(source)


def test_empty_provider_symbol_blocks_configuration_even_when_status_mapped():
    source = complete_map()
    source["symbols"]["US10Y"] = " "

    with pytest.raises(ValueError, match="US10Y"):
        ExternalProviderConfigurationManifest.from_symbol_map(source)


def test_unexpected_asset_blocks_configuration():
    source = complete_map()
    source["symbols"]["EXTRA"] = "P:EXTRA"
    source["status"]["EXTRA"] = "MAPPED"

    with pytest.raises(ValueError, match="unexpected"):
        ExternalProviderConfigurationManifest.from_symbol_map(source)


def test_input_is_detached_and_cannot_mutate_manifest():
    source = complete_map()
    manifest = ExternalProviderConfigurationManifest.from_symbol_map(source)

    source["symbols"]["US500"] = "MUTATED"
    assert manifest.provider_symbols()["US500"] == "P:US500"
    assert manifest.symbol_map["symbols"]["US500"] == "P:US500"

    exported = manifest.snapshot()
    exported["symbol_map"]["symbols"]["US500"] = "EXPORTED-MUTATION"
    assert manifest.symbol_map["symbols"]["US500"] == "P:US500"


def test_manifest_performs_no_provider_discovery_network_or_environment_work():
    manifest = ExternalProviderConfigurationManifest.from_symbol_map(complete_map())

    assert set(manifest.snapshot()) == {
        "name",
        "version",
        "provider",
        "assets",
        "count",
        "complete",
        "observational_only",
        "symbol_map",
    }
    assert manifest.snapshot()["count"] == 7


def test_canonical_order_is_collector_order():
    manifest = ExternalProviderConfigurationManifest.from_symbol_map(complete_map())

    assert tuple(binding.internal_asset for binding in manifest.bindings) == (
        "US500",
        "NASDAQ",
        "DXY",
        "VIX",
        "US10Y",
        "OIL",
        "GOLD",
    )
