# RC54 Readiness and Evidence Protocol

## Scope

RC54 is an observational research flow. It must not influence `ScoreEngine`,
`RiskManager`, `DecisionEngine`, alerts, or order execution.

The protocol separates two independent states:

- `data_ready`: technical integrity of RTD collection, continuity, synchronized
  price, and Delta.
- `trade_context_ready`: MarketStructure and PriceAction provide a directional
  context suitable for observational bucketing.

`SIDEWAYS + PriceAction NONE` means `trade_context_ready=False`. By itself it is
not a technical warning and must not change a clean session to
`COMPLETED_WITH_WARNINGS`.

New captures publish `trade_context_ready_at_start` as the canonical session
field. `context_ready_at_start` is retained only as a compatibility alias. When
both readiness fields exist, the `trade_context_*` value has precedence.

## Live collection

Use the activity preflight and the optional directional coverage gate:

```powershell
python tools/profit_rtd_rc54_5_4_orchestrated_session_runner.py WINV26 `
  --preflight-cycles 90 `
  --preflight-interval 0.25 `
  --cycles 600 `
  --interval 0.25 `
  --max-warmup-cycles 1800 `
  --require-trade-context-at-start `
  --concise-output `
  --progress-every 50 `
  --output-dir data/profit_rtd_rc54_3_2
```

The default RC54.3.3 behavior remains unchanged when
`--require-trade-context-at-start` is omitted. The option exists only to avoid
collecting repeated lateral-only sessions when directional coverage is the
current research need.

`--concise-output` filters only console diagnostics at the orchestrator boundary.
It does not change collection or analysis. Errors, readiness/structure transitions,
and periodic checkpoints remain visible; the default verbose mode remains available.

RC54.5.4 holds a symbol-specific exclusive lock for the entire preflight,
warm-up, and session lifecycle. If another runner for the same symbol already
holds the lock, the new attempt returns `ABORTED_RUNNER_ALREADY_ACTIVE`; it must
not start preflight, warm-up, or capture. The automatic lock supplements the
operator/process check and is not a substitute for confirming that Excel and
RTD are connected to the intended workbook and symbol.

If the market is closed, the preflight fails, or the directional gate reaches
its limit, no 600-cycle session is accepted as evidence.

## Session eligibility

A session is eligible only when all conditions are true:

1. phase is `RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE`;
2. status is `COMPLETED` or `COMPLETED_WITH_WARNINGS`;
3. `data_ready=True` explicitly;
4. `observational_only=True`;
5. samples exist and timestamps are valid and strictly increasing;
6. the file is not a duplicate by resolved path or SHA-256 content;
7. for exact-candle price-action research, its sample interval does not overlap
   another session admitted to the same selection evidence set.

The exact-candle and Brooks auditors retain overlapping evidence for
traceability but quarantine it from clean recomposition. Their rejection record
must identify `TEMPORAL_OVERLAP` and the already admitted session that conflicts
with it. Never count overlapping files as independent exact-candle sessions,
even when their paths or hashes differ.

Technical failures are never reclassified as market context failures. A session
with `data_ready=False` is excluded from RC54.7 and RC54.8. Missing
`data_ready` is also treated as not ready; technical readiness is never inferred
from completion status, price presence, or legacy fields.

The recomposer also verifies that a positive flag is internally consistent. A
session is rejected when it declares `data_ready=True` while recording collection
errors, missing synchronized prices, Delta failures, an unverified price capture,
or inconsistent requested/analyzable/skipped/error cycle continuity.

This rule applies even when tools are called directly. RC54.4, RC54.5, RC54.5.5,
RC54.7, RC54.8, and the offline recomposer require explicit technical readiness
before admitting evidence. RC54.3.3 is the exception because it is a diagnostic
auditor that must be able to explain failures in a problematic session.

RC54.5.5 reports a non-ready directional start under `trade_context_reasons`,
but this diagnostic does not make a technically clean session ineligible. A
lateral session may be retained as valid market-state evidence while contributing
no directional bucket vote.

## Offline recomposition

Run the audit using explicit selection paths:

```powershell
python tools/profit_rtd_rc54_offline_recomposer.py `
  <selection-session-1.json> <selection-session-2.json> <selection-session-3.json> `
  --output data/profit_rtd_rc54_3_2/rc54_offline_recomposition.json
```

The recomposer creates a manifest, runs RC54.4 per accepted selection session,
and recomposes RC54.7. A lateral session remains valid evidence of market state,
but contributes no directional bucket occurrences.

To refresh the complete inventory automatically, including rejected historical
sessions and their reasons:

```powershell
python tools/profit_rtd_rc54_offline_recomposer.py `
  --discover-dir data/profit_rtd_rc54_3_2 `
  --output data/profit_rtd_rc54_3_2/rc54_full_inventory.json
```

Inventory mode reports `INVENTORY_RECOMPOSED_WITH_EXCLUSIONS` when invalid
historical sessions are safely excluded. It still runs robustness only on the
eligible subset.

The inventory also publishes `inventory_summary`, with discovered, accepted,
and rejected session counts plus rejection reasons. These fields are audit
metadata and do not change eligibility.

## Incremental identifiability

RC54.4 reports `incremental_identifiability_by_context` and
`incrementally_identifiable_contexts`. An incremental microstructure effect is
identifiable within BUY or SELL only when that same directional context contains
at least two distinct microbuckets in the session. A single bucket may have many
occurrences while its incremental effect remains mathematically indistinguishable
from the context baseline.

Lack of identifiability is not a technical data failure. Do not reject an
otherwise eligible session, change its completion status, or treat this metric as
an operational signal. Use it only to diagnose why RC54.7 has zero incremental
votes and to guide additional observational coverage.

## Candidate freeze

A bucket can become a robustness candidate only when RC54.7 reports it in
`robustness_candidates`. Current minimum rules are:

- at least 3 supported independent sessions;
- at least 5 occurrences per supported session;
- non-zero incremental votes from at least 3 sessions;
- at least two horizons with a two-thirds directional majority.

Each RC54.7 bucket includes `evidence_gap`. Its
`minimum_additional_sessions_lower_bound` is the smallest theoretical number of
new independent sessions needed to satisfy both supporting-session coverage and
non-zero vote coverage in at least two horizons. It is a lower bound, not a
promise of robustness: new votes must still be directionally consistent.

Do not infer a candidate from pooled means alone. Record the candidate and an ISO
selection cutoff before collecting or evaluating OOS evidence.

## OOS separation

OOS sessions must be provided separately and every sample must be strictly later
than the frozen selection cutoff:

```powershell
python tools/profit_rtd_rc54_offline_recomposer.py `
  <selection-session-1.json> <selection-session-2.json> <selection-session-3.json> `
  --holdout <oos-session-1.json> `
  --holdout <oos-session-2.json> `
  --candidate CONTEXT_BUY_MICRO_NEUTRAL `
  --selection-cutoff 2026-08-31T12:00:00 `
  --output data/profit_rtd_rc54_3_2/rc54_oos_recomposition.json
```

The same path or content cannot appear in both selection and OOS. RC54.8 runs
only when the explicitly supplied candidate is robust in the supplied selection
set.

## Stop conditions

Stop without an operational conclusion when any condition applies:

- fewer than three sessions provide non-zero incremental evidence;
- no robust candidate exists;
- OOS has fewer than 30 candidate occurrences across fewer than two sessions;
- a session has technical data failure;
- market is closed or directional context never becomes ready.

All reports must retain:

- `observational_only=True`;
- `predictive_claim_allowed=False`;
- `score_influence_allowed=False`;
- `risk_influence_allowed=False`;
- `decision_influence_allowed=False`;
- `order_execution_allowed=False`.

## Current checkpoint (2026-08-29)

- six clean selection sessions are accepted by the manifest;
- six additional historical sessions are explicitly rejected because
  `data_ready` is absent or false; overlapping diagnostics also identify two
  collection-error sessions, one Delta-failure session, and one session without
  verified synchronized price capture;
- the full 12-session inventory is persisted as
  `data/profit_rtd_rc54_3_2/rc54_full_inventory_20260829.json`;
- no OOS set is registered under a valid frozen candidate;
- `robustness_candidates=[]`;
- only the 10:34 session makes SELL incrementally identifiable and only the
  11:59 session makes BUY incrementally identifiable;
- every observed bucket currently has a lower bound of at least two additional
  independent sessions before it can satisfy the RC54.7 vote coverage rule;
- current verdict is `MORE_CROSS_SESSION_EVIDENCE_REQUIRED`.
