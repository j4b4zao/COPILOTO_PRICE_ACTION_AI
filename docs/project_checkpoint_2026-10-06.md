# Project checkpoint — 2026-10-06

## Current validated state

- Core Strategy -> Score -> Risk -> Decision -> Alert remains validated and isolated from observational external context.
- External observational chain validated through:
  - Monitor RC1
  - Observational View RC2
  - Intermarket Observational Synthesis RC3
  - External Observational Context RC4
  - Read-only Console Projection RC4.1
- RC4.1 real run validated in degraded conditions:
  - context PARTIAL_CONTEXT
  - readiness DATA_NOT_READY
  - usable context 1/7
  - US500 STALE
  - NASDAQ STALE
  - DXY MISSING
  - VIX AVAILABLE
  - US10Y/OIL/GOLD DEGRADED
  - operational influence disabled
- FMP index freshness probe RC1 validated offline (5 tests).
- Real FMP freshness probe confirmed stale provider timestamps for ^GSPC, ^IXIC and ^VIX relative to the 3600-second threshold.
- FMP quote vs intraday 1-minute comparator RC1 created and validated offline.
- Combined comparator/freshness gate: 10 passed.
- No staleness threshold was relaxed.
- No external context was promoted into Score/Risk/Decision/Alert/orders.
- No automatic external activation was introduced.

## Next session

During U.S. market hours, run the real FMP comparison for:
- ^GSPC
- ^IXIC
- ^VIX

Compare:
- /stable/quote
- /stable/historical-chart/1min

Goal: determine whether the 1-minute endpoint provides fresher observational data without weakening timestamp/freshness safeguards.

If the intraday timestamp is timezone-naive, keep it fail-closed as AMBIGUOUS_TIMEZONE until its semantics are explicitly validated.

## Remaining high-level roadmap

- Resolve/finalize freshness source for US500/NASDAQ/VIX.
- DXY remains unresolved without an accepted exact/free source.
- US10Y remains unresolved under the current no-paid-source policy.
- Reassess OIL freshness source if needed.
- Complete external observational data-quality validation across multiple live sessions.
- Continue advanced Order Flow / Book / Times & Trades validation and integration work.
- Complete multi-timeframe / market-regime and remaining planned dashboards/operator presentation where still pending.
- Only after evidence and explicit approval: evaluate whether any external/research context deserves controlled promotion into operational decision logic.
- Final integrated regression, paper/simulation validation, documentation and release closeout.

## Safety invariants

- observational_only = true for external chain
- operational_influence_allowed = false
- automatic_activation = false
- explicit timestamps for manual external tools
- no implicit clock/provider activation in core
- no Bot.mostrar external collection wiring
- no threshold relaxation to hide stale data
