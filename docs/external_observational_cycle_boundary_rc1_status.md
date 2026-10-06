# External Observational Cycle Boundary RC1 — Closed

Checkpoint: 2026-10-06

## Scope

The boundary composes the existing external observational service, producer and
presentation cycle without activating them at construction time. Provider
selection and cycle policy remain caller-owned and explicit.

No automatic Bot loop, SystemInitializer, AnalysisPipeline, ScoreEngine,
RiskManager, DecisionEngine, AlertManager or execution wiring is authorized.

## Validated contract

- Construction requires an explicit provider exposing fetch(symbol).
- Construction performs no provider fetch.
- ExternalObservationalCyclePolicy requires an explicit timezone-aware
  reference timestamp and staleness threshold.
- Optional ProviderSymbolMap snapshot evidence is detached at policy creation.
- produce(policy) performs the explicit observational cycle.
- present(bot, context, policy) uses the already validated completed-audit
  presentation seam.
- Failed later collections cannot reuse an earlier audit.
- The boundary owns no default clock, policy, runtime activation or audit cache.

## Evidence

Local results reported for this checkpoint:

- Boundary + Presentation Cycle + Producer focused gate: 30 passed.
- Combined external/bridge/dashboard/Bot/Boundary gate: 559 passed.
- Operational regression gate covering Risk, Score, Decision, Order Flow and
  Profit RTD RC51: 87 passed.

No failures were reported in these gates.

## Repository checkpoint

- Boundary implementation commit: fbfd6817c1180fbe2ddb2413b4904b81b1bd9a39
- Boundary acceptance tests / validated implementation HEAD:
  a3269e63c765fcc0af09a89c46ecb8515ba9f967
- Working branch: brooks-stop-target-exact-audit-20260912

## Safety invariants

- observational_only remains mandatory.
- External presentation remains disabled by default in Bot.mostrar.
- Bot.executar remains unchanged and does not invoke this boundary.
- SystemInitializer and AnalysisPipeline remain outside this activation path.
- No external evidence affects trading decisions or execution.
- No provider is selected implicitly.
- No timestamp is inferred from WIN/WDO AnalysisContext.

## Next safe step

Add an explicit manual activation facade/entry point that can be invoked by a
caller for one external observational cycle. It must require a configured
boundary/policy (or equivalent explicit dependencies), must not become part of
Bot.executar, and must preserve fail-closed/no-cache behavior. A real provider
or environment-backed configuration must not be selected implicitly during
this step.
