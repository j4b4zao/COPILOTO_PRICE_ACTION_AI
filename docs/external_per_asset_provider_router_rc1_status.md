# External Per-Asset Provider Router RC1 — Validation Status

Date: 2026-10-06

## Status

VALIDATED.

The per-asset external provider router remains observational-only and does not authorize operational influence.

## Validation evidence

- Focused router contract: 6 passed in 2.12s.
- Intermediate external/provider/collector gate: 221 passed, 2 warnings in 17.24s.
- Expanded external gate (excluding legacy script-style test_external_provider_robustness.py): 672 passed, 2 warnings in 24.49s.
- Operational regression gate (Strategy / Score / Risk / Decision / Alert pipeline coverage selected from current suite): 15 passed in 5.36s.

## Known legacy test issues

- tests/test_external_market_collector.py emits PytestReturnNotNoneWarning because legacy tests return bool instead of asserting.
- tests/test_external_provider_robustness.py is a manual/script-style legacy validation file collected by pytest; helper testar_coleta(nome, dados, deve_ser_valido) is mistaken for a pytest test and requests nonexistent fixtures. This was not caused by RC1 and was excluded from the expanded gate rather than modified out of scope.

## Safety invariants retained

- observational_only = true
- operational_influence_allowed = false
- partial per-asset routing fails closed for unconfigured assets
- no Bot integration
- no automatic producer/clock integration
- no network in tests
- no weakening of the existing complete single-provider configuration manifest
- no automatic provider-symbol guessing or ambiguous instrument promotion

## Next step

Evaluate and prove real data providers per asset for US500, NASDAQ, DXY, VIX, US10Y and OIL. Twelve Data GOLD (XAU/USD) is the only currently demonstrated quote path under the tested account; other assets remain unpromoted until provider identity, availability, freshness and timestamp semantics are explicitly verified.
