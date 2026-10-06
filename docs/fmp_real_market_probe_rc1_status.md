# FMP Real Market Probe RC1 — Evidence Status

Date: 2026-10-06

## Safety

Evidence-only manual probe. No ProviderSymbolMap, manifest, router routes, Bot integration, or operational influence was created.

## Real probe results

### Quote returned with explicit provider identity

- US500 candidate ^GSPC
  - provider symbol: ^GSPC
  - provider name: S&P 500
  - exchange: INDEX
  - Unix timestamp returned
  - status: QUOTE_RETURNED
- NASDAQ candidate ^IXIC
  - provider symbol: ^IXIC
  - provider name: NASDAQ Composite
  - exchange: INDEX
  - Unix timestamp returned
  - status: QUOTE_RETURNED
- VIX candidate ^VIX
  - provider symbol: ^VIX
  - provider name: CBOE Volatility Index
  - exchange: INDEX
  - Unix timestamp returned
  - status: QUOTE_RETURNED

These three identities are provider-evidenced candidates. They are not yet automatically promoted into router configuration.

### Blocked / unresolved

- DXY candidate DX-Y.NYB: HTTP 402
- DXY candidate DXY: HTTP 402
- OIL candidate CLUSD: HTTP 402
- OIL candidate CL=F: HTTP 402
- US10Y was intentionally excluded from RC1 rather than guessed.

HTTP 402 is retained as provider/access evidence and is not interpreted as proof that a candidate identity is invalid.

## Current real-provider evidence matrix

- US500: FMP quote path demonstrated (^GSPC)
- NASDAQ: FMP quote path demonstrated (^IXIC)
- VIX: FMP quote path demonstrated (^VIX)
- GOLD: Twelve Data quote path previously demonstrated (XAU/USD)
- DXY: unresolved
- US10Y: unresolved
- OIL: unresolved / Twelve Data identity WTI/USD previously recognized but inaccessible on tested plan; FMP candidates returned 402

## Next step

Create an FMP transport/adapter path only after timestamp semantics are explicitly normalized and tested. Continue provider research/probes for DXY, US10Y and OIL. No operational promotion until those contracts are separately validated.
