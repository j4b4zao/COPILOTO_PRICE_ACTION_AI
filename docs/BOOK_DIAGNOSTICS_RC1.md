# BookDiagnostics RC1

## Objective

Provide a passive consolidation boundary for experimental diagnostics derived from the three Brooks Price Action books.

## Safety contract

`BookDiagnosticsResult` and `BookDiagnosticsEngine` do not participate in Strategy, Score, Risk, Decision or execution.

RC1 intentionally remains outside `AnalysisContext` and `AnalysisPipeline`. This allows the result/engine contract and selected diagnostics to be tested independently before any pipeline registration.

## RC1 diagnostics

- AlwaysInDynamics
- TrendStrengthDynamics

The engine produces only a passive synthesis:

- `directional_bias`
- `alignment`
- `quality_score`
- `confidence`

## Promotion path

1. Unit-test the isolated engine/result contract.
2. Add the result to AnalysisContext without consumer access.
3. Register the engine in AnalysisPipeline as observability-only.
4. Run controlled replay/A-B comparisons.
5. Only after measurable value, consider promotion to Evidence/Context.
6. Score/Risk/Decision changes require a separate release and regression suite.

## RC1 non-goals

- No score bonus or penalty.
- No risk veto.
- No decision gate.
- No order generation.
- No direct mutation of PriceActionResult.
