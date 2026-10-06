# External Observational Manual Activation RC1 — Closed

Checkpoint: 2026-10-06

## Scope
Manual opt-in activation gate around the validated external observational cycle.
No automatic Bot loop, SystemInitializer, AnalysisPipeline, Score/Risk/Decision,
Alert or execution wiring is authorized.

## Contract
- Exact enabled=True is required before collection.
- Default/False activation fails closed without provider access.
- Non-bool activation values fail closed.
- Provider, policy, reference timestamp and symbol-map ownership remain outside.
- Invalid policy or Bot fails before collection.
- Failed later collection cannot present or reuse a previous audit.
- The activation object retains only the configured boundary.

## Evidence
- Manual Activation + Boundary + Presentation + Producer focused gate: 44 passed.
- Combined external/bridge/dashboard/Bot gate: 573 passed.
- Operational Risk/Score/Decision/Order Flow/Profit RTD gate: 87 passed.
- No failures reported.

## Repository checkpoint
- Manual activation implementation: aa4bde74b3ccfd4b9ab6b820ddd368c3f51b0814
- Manual activation acceptance tests / validated HEAD:
  a65455b32854f5bcc85e998612d32d4203985383
- Working branch: brooks-stop-target-exact-audit-20260912

## Next safe step
Audit existing provider/symbol-resolution assets and define a concrete external
provider configuration contract for US500, NASDAQ, DXY, VIX, US10Y, OIL and
GOLD. Do not activate network access, guess aliases, embed credentials, or join
Bot.executar during configuration design.
