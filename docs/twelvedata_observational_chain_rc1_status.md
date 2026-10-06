# Twelve Data Observational Chain RC1 — Offline Validation

Checkpoint: 2026-10-06

## Validated chain
TwelveDataQuoteTransport -> ExternalConfiguredProviderAdapter ->
ExternalContextService/Collector -> ExternalObservationalSnapshot ->
IntermarketExternalContextBridge audit -> explicit Manual Activation boundary.

## Evidence
- Focused chain gate after readiness-contract correction: 71 passed in 4.21s.
- The readiness contract is status-based: DATA_READY / DATA_NOT_READY.
- No production module was changed for that correction; only E2E test assertions.

## Safety properties
- Seven canonical assets remain US500, NASDAQ, DXY, VIX, US10Y, OIL, GOLD.
- Provider symbols come only from an explicitly validated manifest.
- Transport construction is inert.
- API key is explicit; no implicit environment read in the transport.
- Tests inject HTTP responses; no real network is required.
- Disabled manual activation performs zero provider requests.
- Provider identity is preserved and verified against the explicit symbol map.
- Timezone-naive provider timestamps are not silently assigned a timezone;
  they fail audit as INVALID_TIMESTAMP / DATA_NOT_READY.
- No Bot.executar, SystemInitializer, AnalysisPipeline, Score, Risk, Decision,
  Alert or order integration.

## Relevant commits
- Twelve Data quote transport: 14214464f67b441dd994fe3adb85107da37eee36
- Transport acceptance tests: 4302979a419b8852828c3c9ade40aacd49173803
- Offline E2E observational chain: d77267edaf64faafddff5663d0af47067ad7541c
- Readiness assertion correction / validated HEAD:
  cb7930c6dd7668648534f1438d020122fb3e4d05

## Next step
Create a separate manual real-provider probe. It must require explicit invocation
and explicit credentials/configuration, print audit evidence, avoid automatic
symbol discovery/selection, and remain outside Bot.executar().
