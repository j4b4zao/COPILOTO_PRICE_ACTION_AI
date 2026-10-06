# External Provider Configuration + Adapter RC1 — Closed

Checkpoint: 2026-10-06

## Scope
Offline, explicit provider-identity configuration for the seven canonical
external observational assets, plus an injected transport adapter.

Canonical assets:
US500, NASDAQ, DXY, VIX, US10Y, OIL, GOLD.

## Contracts
- Configuration requires every canonical asset to be explicitly MAPPED.
- Missing, empty, ambiguous, unresolved, unavailable, not-found and provider-error
  states fail closed.
- Provider identity is mandatory.
- Unexpected assets fail closed.
- Manifest input/output is detached.
- Adapter translates canonical asset -> validated provider symbol.
- Adapter enriches successful quotes with provider_name/provider_symbol evidence.
- Conflicting transport identity fails closed.
- Construction performs no fetch, discovery, environment lookup or network work.
- No clock, cache or network configuration is owned by the adapter.
- Observational collector integration remains compatible.

## Evidence
- Focused Manifest + Adapter + Manual Activation + Boundary gate: 50 passed.
- Expanded external/bridge/dashboard/Bot gate: 601 passed in 11.16s.
- Operational Risk/Score/Decision/Order Flow/Profit RTD gate: 87 passed in 7.04s.
- No failures reported.

## Repository checkpoints
- Manifest implementation: 6cd530dbd68a3e2524d7b855d284de0210fe9d2d
- Manifest acceptance tests: 82cc62b094d9120bef7a0b80a63debe79d29f537
- Configured adapter implementation: c5601845128f6a20f792a12b7c031a308bd6b78c
- Configured adapter acceptance tests / validated HEAD:
  6d6956aa02e2ccc28452dc025c757292778ba553
- Branch: brooks-stop-target-exact-audit-20260912

## Safety invariants
Observational only. No Score, Risk, Decision, Alert or order influence.
No Bot.executar, SystemInitializer or AnalysisPipeline integration.
No implicit provider selection, symbol guessing, credential loading or network
activation.

## Next safe step
Audit the existing Twelve Data transport/provider contracts and build a
controlled adapter/configuration seam whose tests use injected offline HTTP
responses. Real API execution remains a separate explicit/manual step.
