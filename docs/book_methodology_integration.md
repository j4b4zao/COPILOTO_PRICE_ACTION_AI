# Book-derived methodology integration

Status: observational foundation, RC1. No operational authorization.

## Sources reviewed

- Tim Richards, *Investing Psychology: The Effects of Behavioral Finance on
  Investment Choice and Bias*.
- Van K. Tharp, *Trading Beyond the Matrix*.
- John J. Murphy, *Trading with Intermarket Analysis*.
- Van K. Tharp, *Trade Your Way to Financial Freedom*, second edition.

The books are reference material, not specifications. Claims are admitted only
when they can be represented as explicit data, tested out of sample, and kept
separate from ScoreEngine, RiskManager, DecisionEngine, alerts, and execution.

## Accepted methodology

### Decision hygiene and psychology

- Write the thesis and invalidation condition before observing the outcome.
- Record disconfirming evidence, not only supporting evidence.
- Use a short checklist, minimize decisions under time pressure, and retain an
  immutable decision journal.
- Review outcomes and distinguish process quality from outcome quality.
- Define a trading mistake as a documented rule violation, record its code, and
  measure its cost in R rather than relying on memory.
- Treat beliefs, confidence, emotion, authority, herding, anchoring, hindsight,
  availability, loss aversion, overtrading, and intermittent reinforcement as
  hypotheses about process risk, never clinical diagnoses or market signals.

### System quality and risk research

- Normalize results by initial risk (R) and report the full R-multiple sample.
- Report expectancy, dispersion, win/loss/breakeven rates, cumulative R,
  peak-to-trough drawdown in R, sample sufficiency, and opportunity-adjusted
  expectancy. Never infer robustness from win rate alone.
- Predeclare objectives and constraints before system selection. Position sizing
  belongs to a later risk-validation stage and must be simulated against the
  empirical R distribution and worst-case scenarios before any operational use.
- Evaluate a system separately by market type/regime; do not assume one rule set
  transfers across trend, direction, or volatility regimes.

### Intermarket research

- Model bonds/rates, equities, commodities, currencies, and sectors as context.
- Use rolling returns, correlations, relative-strength ratios, lead/lag tests,
  breadth, and regime segmentation. Relationships must be measured in the
  current sample because correlations change over time.
- Treat business-cycle and cross-asset narratives as hypotheses. They may enrich
  an offline context report but cannot become fixed causal rules or direct trade
  signals without frozen selection, independent OOS, and stability testing.

## Deferred until inputs exist

- Intermarket features require timestamp-aligned, survivorship-aware data for
  the relevant Brazilian index future and external proxies. Missing/stale data
  must produce `DATA_NOT_READY`, never a neutral value.
- Position-sizing experiments require a frozen strategy, empirical R-multiple
  distribution, costs/slippage, capital constraints, and acceptable drawdown
  objectives. The observer implemented in RC1 does not size positions.
- Bias calibration requires enough precommitted journal entries to compare
  process gaps with later outcomes without leakage.

## Excluded from automation

- Spiritual or metaphysical transformation claims and subjective inner guidance.
- Personality labels, mental-health diagnoses, or claims inferred from P&L.
- Historical macro relationships encoded as timeless laws.
- Any automatic score, risk, decision, alert, or order effect derived directly
  from the books.

## RC1 implementation

`analysis/research/book_methodology_observer.py` provides two pure diagnostics:

1. a decision-process audit for precommitment, invalidation, disconfirming
   evidence, checklist, time pressure, outcome review, and rule violations;
2. an R-multiple report for expectancy, dispersion, rates, drawdown, sample
   sufficiency, and opportunity-adjusted expectancy.

Every result hard-codes observational-only and all influence permissions false.
The module is intentionally not imported by the live analysis pipeline.

## Next controlled increments

1. Add immutable journal serialization for the RC1 observations.
2. Add regime-stratified R reports with minimum sample and cross-session rules.
3. Define an intermarket data contract and freshness/alignment auditor.
4. Implement rolling relationship diagnostics offline, then freeze hypotheses.
5. Collect independent evidence before considering any integration beyond
   reporting. Operational promotion is outside this phase.

RC1 now includes steps 2 and 3 as isolated foundations: regime samples are
reported separately and any missing, stale, or future-dated intermarket input
produces `DATA_NOT_READY`. Rolling relationships and provider integration remain
deferred.

The next RC1 increment adds a SHA-256 hash-chained journal. Thesis, invalidation,
disconfirming evidence, rule violations, outcomes, and violation cost in R become
tamper-evident; altered history is rejected before an entry can be appended. It
also adds rolling pair correlation over exact timestamp intersections. A measured
correlation remains descriptive and explicitly disallows predictive or operational
claims. Provider integration and lead/lag hypothesis testing remain deferred.

## Candlestick and Elder evidence increment

Additional references reviewed:

- *The Candlestick Trading Bible* (Portuguese translation supplied by the user).
- Alexander Elder, *Trading for a Living* (Portuguese edition supplied by the user).

The project already detects doji, hammer, shooting star, bullish/bearish
engulfing, inside bar, and outside bar. Those operational definitions were not
changed. The books' diagrams and narratives do not justify competing detectors
or automatic score increases.

The viable increment is an offline evidence protocol. Each existing pattern
classification is evaluated separately by market regime, timeframe, and
location context. Forward return and optional relative volume are reported per
bucket. Every bucket must meet its own minimum sample; aggregation across
different contexts is forbidden. A pattern name describes candle geometry, not
a trade direction or a predictive claim.

Elder's multi-timeframe and price/volume ideas are retained as testable research
hypotheses. The live project already has multi-timeframe analysis, so Triple
Screen is not added as a second operational gate. Instead, future offline
experiments may compare results across frozen horizon combinations and measure
whether volume confirmation is stable OOS. Force Index and Elder-Ray remain
deferred until their inputs, formula variants, costs, and comparison baselines
are frozen in a dedicated protocol.

Excluded from implementation:

- claims that a candle pattern is inherently high-probability or predictive;
- universal confluence, support/resistance, Fibonacci, or fixed risk rules;
- inferred institutional intent or crowd psychology treated as ground truth;
- any new effect on ScoreEngine, RiskManager, DecisionEngine, alerts, or orders.

`analysis/research/price_action_evidence_observer.py` implements the isolated
bucket report. It is not imported by the analysis pipeline. All operational and
predictive permissions are hard-disabled in its result contract.
