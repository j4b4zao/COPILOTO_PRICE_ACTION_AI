# External unresolved assets provider research RC1

Date: 2026-10-06

## Scope and safety

Research-only provider decision record. No provider is promoted by this document.
No ProviderSymbolMap, manifest, router route, Score/Risk/Decision/Alert input, order
path, automatic clock, or automatic network producer is created.

## Current evidence matrix

| Asset | Candidate/source | Identity evidence | Intraday price/yield evidence | Timestamp evidence | Status |
|---|---|---|---|---|---|
| US500 | FMP ^GSPC | demonstrated | demonstrated | FMP Unix seconds -> UTC ISO | READY_FOR_OBSERVATIONAL_CONFIGURATION |
| NASDAQ | FMP ^IXIC | demonstrated | demonstrated | FMP Unix seconds -> UTC ISO | READY_FOR_OBSERVATIONAL_CONFIGURATION |
| VIX | FMP ^VIX | demonstrated | demonstrated | FMP Unix seconds -> UTC ISO | READY_FOR_OBSERVATIONAL_CONFIGURATION |
| GOLD | Twelve Data XAU/USD | demonstrated | demonstrated | unresolved: quote datetime was date-only; numeric timestamp semantics not yet approved | BLOCKED_TIMESTAMP |
| DXY | ICE U.S. Dollar Index | canonical identity and intraday product documented by ICE | no usable project credential/transport demonstrated | not demonstrated in project | BLOCKED_ACCESS |
| US10Y | U.S. Treasury official feed | canonical daily 10Y yield exists | official Treasury feed is daily, not accepted for intraday requirement | daily only | BLOCKED_INTRADAY_SOURCE |
| US10Y | Bonds API US/10Y | candidate provider documents intraday snapshots | not yet demonstrated with project-side real probe | documented UTC fetched_at, not yet empirically demonstrated | CANDIDATE_NOT_APPROVED |
| OIL | Massive CL / NYMEX | product and dated contract discovery demonstrated | CLF7 quote probe returned HTTP 403 | endpoint semantics documented, but no successful real quote | BLOCKED_ACCESS |
| OIL | CME Group CL | canonical exchange/product identity and real-time futures API documented | project has no CME API access demonstrated | not demonstrated in project | CANDIDATE_NOT_APPROVED |

## Decisions

1. Do not treat ETF, CFD, synthetic index, or unrelated futures proxy as DXY or US10Y.
2. Do not weaken the intraday requirement for US10Y.
3. Do not promote Massive OIL after HTTP 403; access failure is not identity failure.
4. Do not approve Bonds API US10Y from documentation alone. It requires an isolated,
   user-invoked real probe with explicit date and no automatic integration.
5. Do not add ICE/CME commercial integrations without explicit credentials/access and
   an isolated transport validation.
6. Keep the per-asset multi-provider architecture; partial observational configuration
   remains preferable to accepting weak proxies.

## Next empirical gate

US10Y: if a Bonds API credential is intentionally configured by the user, create/run
an isolated manual probe for country=US, maturity=10Y, explicit YYYY-MM-DD date.
The probe must prove a real yield plus timezone-aware observation timestamp before
any provider adapter/router work.

DXY: continue provider search for the canonical ICE U.S. Dollar Index with usable
intraday access. Do not substitute an ETF.

OIL: seek a provider that exposes actual CL/WTI futures or canonical WTI intraday
price with usable access; Massive remains identity-evidence only until quote access
is demonstrated.
