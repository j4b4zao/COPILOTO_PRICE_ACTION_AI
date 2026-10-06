# FMP Partial Observational Chain RC1 — Validation Status

Date: 2026-10-06

## Scope

Validated offline chain:

FMPQuoteTransport -> ExternalPerAssetProviderConfiguration ->
ExternalPartialConfiguredProviderAdapter -> ExternalPerAssetProviderRouter ->
ExternalMarketCollector

Explicit provider-evidenced FMP bindings:
- US500 -> ^GSPC
- NASDAQ -> ^IXIC
- VIX -> ^VIX

No DXY, US10Y, OIL or GOLD route is created by this milestone.

## Validation

Command gate covered:
- tests/test_fmp_quote_transport_rc1.py
- tests/test_external_per_asset_provider_configuration_rc1.py
- tests/test_external_per_asset_provider_router_rc1.py

User validation result:
- 32 passed in 5.30s

## Safety invariants

- observational_only = true
- operational influence remains disabled
- no Bot integration
- no environment reads in core configuration/router
- no automatic discovery
- no implicit clock
- Unix provider timestamp is explicitly converted to timezone-aware UTC ISO-8601 by FMPQuoteTransport
- partial coverage remains incomplete/fail-closed
- existing complete single-provider manifest contract was not weakened

## Next provider evidence work

DXY, US10Y and OIL remain unresolved for complete external context.
Provider research/probes must establish identity, availability, timestamp semantics,
and plan access before any new binding is approved.
