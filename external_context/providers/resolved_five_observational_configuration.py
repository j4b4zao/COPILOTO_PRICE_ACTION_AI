"""Resolved-five observational external provider configuration RC1.

Explicitly composes only evidence-validated transports:
US500/NASDAQ/VIX via FMP, GOLD via Twelve Data, OIL via Americas Oil Watch.
DXY and US10Y deliberately remain unrouted. Construction is explicit: credentials
are arguments, never environment reads, and no request occurs during construction.
"""
from external_context.providers.external_per_asset_provider_configuration import (
    ExternalPerAssetProviderConfiguration, ExternalPartialConfiguredProviderAdapter,
)
from external_context.providers.external_per_asset_provider_router import ExternalPerAssetProviderRouter
from external_context.providers.fmp_quote_transport import FMPQuoteTransport
from external_context.providers.twelvedata_quote_transport import TwelveDataQuoteTransport
from external_context.providers.americas_oil_watch_wti_transport import AmericasOilWatchWTITransport

FMP_SYMBOLS={"US500":"^GSPC","NASDAQ":"^IXIC","VIX":"^VIX"}
GOLD_SYMBOLS={"GOLD":"XAU/USD"}
OIL_SYMBOLS={"OIL":"CL=F"}

def build_resolved_five_observational_router(*,fmp_api_key,twelvedata_api_key,
        fmp_opener=None,twelvedata_opener=None,oil_opener=None):
    fmp=ExternalPartialConfiguredProviderAdapter(
        ExternalPerAssetProviderConfiguration.create(provider_name="FMP",symbols=FMP_SYMBOLS),
        FMPQuoteTransport(api_key=fmp_api_key,opener=fmp_opener))
    gold=ExternalPartialConfiguredProviderAdapter(
        ExternalPerAssetProviderConfiguration.create(provider_name="Twelve Data",symbols=GOLD_SYMBOLS),
        TwelveDataQuoteTransport(api_key=twelvedata_api_key,opener=twelvedata_opener))
    oil=ExternalPartialConfiguredProviderAdapter(
        ExternalPerAssetProviderConfiguration.create(provider_name="Americas Oil Watch / Yahoo Finance CL=F",symbols=OIL_SYMBOLS),
        AmericasOilWatchWTITransport(opener=oil_opener))
    return ExternalPerAssetProviderRouter({
        "US500":fmp,"NASDAQ":fmp,"VIX":fmp,"GOLD":gold,"OIL":oil,
    })

def snapshot():
    return {"name":"ResolvedFiveObservationalExternalConfiguration","version":"RC1",
        "configured_assets":("US500","NASDAQ","VIX","OIL","GOLD"),
        "missing_assets":("DXY","US10Y"),"complete":False,
        "observational_only":True,"operational_influence_allowed":False,
        "automatic_activation":False,"environment_reads":False}
